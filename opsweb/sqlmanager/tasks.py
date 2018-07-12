from opsweb.celery import app
from dashboard.utils.ws_dingding import DingDingMsgSend
from dashboard.utils.ws_weixin import WxMsgSend
from celery.utils.log import get_task_logger
from celery import shared_task
from api.thirdapi.inception_api import InceptionApi
from opsweb.settings import MEDIA_ROOT
from sqlmanager.models import SQLRollBackModel,SQLCheckTmpModel
# from sqlmanager.inception_relate import inception_init_func
import os
import sys

celery_log_info = get_task_logger("info_logger")
celery_log_error = get_task_logger("error_logger")

upload_dir = MEDIA_ROOT + 'sqlfile/'

''' 拆分一个语句块或者sql文件为单条sql '''
@shared_task(bind=True,name="SQLCheckAndSplit")
def SQLCheckAndSplit(self,sql_obj_list):
    ''' 要传一个 sql_obj 的列表过来；主要是考虑sql工单包含多个sql块或文件的情况,以免循环运行该后台任务 '''
    for sql_obj in sql_obj_list:
        ret = {"result":0}
        sql_block = sql_obj.sql_block
        sql_file_url = sql_obj.sql_file_url
        db_obj = sql_obj.db_name
        env = sql_obj.env

        if sql_file_url:
            sql_file_dir = upload_dir + sql_file_url
            if not os.path.exists(sql_file_dir):
                celery_log_error.error("该文件 '%s'不存在或已被删除..." % (sql_file_dir))
                break
            with open(sql_file_dir, 'r') as f:
                sql_detail = f.read()

        try:
            db_master_ip = db_obj.cluster_name.get(env__exact=env).dbinstancemodel_set.get(role__exact='master').ins_ip.private_ip
        except Exception as e:
            celery_log_error.error("获取 DBModel 对象失败，或者获取 DB 主实例的IP失败,错误信息： %s" % (e.args))
            break

        sql_str = sql_block if sql_block else sql_detail
        inc_obj = InceptionApi("root", "Abcd1234!", db_master_ip, db_obj.name, sql_str=sql_str)
        inc_obj.inception_check_to_split(sql_obj)

''' 执行SQL '''
@shared_task(bind=True,name="SQLExec")
def SQLExec(self,sql_exec_list,s_obj,user_obj):
    try:
        db_master_ip = s_obj.db_name.cluster_name.get(env__exact=s_obj.env).dbinstancemodel_set.get(role__exact='master').ins_ip.private_ip
    except Exception as e:
        celery_log_error.error("获取 DBModel 对象失败，或者获取 DB 主实例的IP失败,错误信息： %s" % (e.args))
        return

    for s in sql_exec_list:
        inc_obj = InceptionApi("root", "Abcd1234!", db_master_ip, s_obj.db_name.name, sql_str=s.sql)
        ret = inc_obj.inception_exec()
        ret["db_master_ip"] = db_master_ip
        if ret["result"] == 1:
            break
        inc_check_result = ret["inc_result"][1]
        del ret["inc_result"]
        s_obj.status = '1'
        s_obj.exec_user = user_obj
        s.errormessage = inc_check_result[4]
        s.affected_rows = inc_check_result[6]
        '''eval(inc_check_result[7]) 使得 s.seqnum 的值 "'1528168691_434985_2'" 变成 '1528168691_434985_2' '''
        s.seqnum = eval(inc_check_result[7])
        s.execute_time = inc_check_result[9]
        s.backup_dbname = inc_check_result[8]
        if inc_check_result[4] != 'None':
            celery_log_error.error("SQLExecDetailModel 模型更新对象id: %s 执行有错误,错误信息: %s" % (s.id, inc_check_result[4]))
            try:
                s.exec_result = "failed"
                s.backup_result = "noexec"
                s_obj.exec_status = "1"
                s.save()
                s_obj.save(update_fields=["exec_status","status","exec_user"])
            except Exception as e:
                celery_log_error.error("SQLExecDetailModel 模型更新对象id: %s 失败,错误信息: %s" %(s.id,e.args))
            finally:
                break

        if inc_check_result[3].split("\n")[0] != 'Execute Successfully':
            celery_log_error.error("SQLExecDetailModel 模型更新对象id: %s 执行失败,执行结果: %s" % (s.id,inc_check_result[3].split("\n")[0]))
            try:
                s.exec_result = "failed"
                s.backup_result = "noexec"
                s_obj.exec_status = "1"
                s.save()
                s_obj.save(update_fields=["exec_status","status","exec_user"])
            except Exception as e:
                celery_log_error.error("SQLExecDetailModel 模型保存更新对象id: %s 失败,错误信息: %s" % (s.id, e.args))
            finally:
                break

        try:
            s.backup_result = "failed" if inc_check_result[3].split("\n")[1] != 'Backup successfully' else "success"
            s.exec_result = "success"
            s_obj.exec_status = "0"
            s.save()
            s_obj.save(update_fields=["exec_status","status","exec_user"])
        except Exception as e:
            celery_log_error.error("SQLExecDetailModel 模型保存更新对象id: %s 失败,错误信息: %s" % (s.id, e.args))
            break

    ''' 后台执行获取备份语句 '''
    SQLBackupSync.delay(s_obj)

''' 回滚SQL '''
@shared_task(bind=True,name="SQLRollback")
def SQLRollback(self,s_exec_obj,myuser):
    try:
        db_master_ip = s_exec_obj.sql_block.db_name.cluster_name.get(env__exact=s_exec_obj.sql_block.env).dbinstancemodel_set.get(role__exact='master').ins_ip.private_ip
    except Exception as e:
        celery_log_error.error("获取 DBModel 对象失败，或者获取 DB 主实例的IP失败,错误信息： %s" % (e.args))
        return

    for sr_obj in s_exec_obj.sqlrollbackmodel_set.all():
        inc_obj = InceptionApi("root", "Abcd1234!", db_master_ip, s_exec_obj.sql_block.db_name.name, sql_str=sr_obj.sql_rollback)
        ret = inc_obj.inception_exec()
        ret["db_master_ip"] = db_master_ip
        if ret["result"] == 1:
            celery_log_error.error(ret["msg"])
            break

        inc_rollback_result = ret["inc_result"][1]
        del ret["inc_result"]
        sr_obj.rollback_exec_user = myuser
        sr_obj.rollback_errmsg = inc_rollback_result[4]
        sr_obj.rollback_affected_rows = inc_rollback_result[6]
        '''eval(inc_check_result[7]) 使得 s.seqnum 的值 "'1528168691_434985_2'" 变成 '1528168691_434985_2' '''
        sr_obj.rollback_seqnum = eval(inc_rollback_result[7])
        sr_obj.rollback_execute_time = inc_rollback_result[9]
        sr_obj.rollback_backup_dbname = inc_rollback_result[8]
        sr_obj.rollback_sql_sha1 = inc_rollback_result[10]

        if inc_rollback_result[4] != 'None':
            try:
                sr_obj.sql_rollback_result = "failed"
                sr_obj.save()
                s_exec_obj.sql_block.save(update_fields=[ "status"])
            except Exception as e:
                err_msg = "SQLExecDetailModel 模型更新对象 id: %s 失败 \
                        或者SQLRollBackModel 模型更新对象 id: %s 失败,错误信息: %s" \
                          % (s_exec_obj.id, sr_obj.id, e.args)
                celery_log_error.error(err_msg)
            finally:
                celery_log_error.error("执行 SQLRollBackModel 模型对象 id: %s 对应的回滚语句失败,错误信息: %s " % (sr_obj.id, inc_rollback_result[4]))
                break

        if inc_rollback_result[3].split("\n")[0] != 'Execute Successfully':
            try:
                s_exec_obj.sqlrollbackmodel.sql_rollback_result = "failed"
                s_exec_obj.sqlrollbackmodel.save()
                s_exec_obj.sql_block.save(update_fields=["status"])
            except Exception as e:
                celery_log_error.error("SQLExecDetailModel 模型更新对象 id: %s 失败 \
                                或者SQLRollBackModel 模型更新对象 id: %s 失败,错误信息: %s" \
                                    % (s_exec_obj.id, sr_obj.id, e.args))
            finally:
                celery_log_error.error("执行 SQLRollBackModel 模型对象 id: %s 对应的回滚语句失败,错误信息: %s" % (sr_obj.id, inc_rollback_result[3].split("\n")[0]))
                break

        try:
            sr_obj.sql_rollback_result = "success"
            sr_obj.save()
            s_exec_obj.sql_block.save(update_fields=["status"])
        except Exception as e:
            err_msg = "SQLExecDetailModel 模型更新对象 id: %s 失败 \
                    或者SQLRollBackModel 模型更新对象 id: %s 失败,错误信息: %s" \
                        % (s_exec_obj.id, sr_obj.id, e.args)
            celery_log_error.error(err_msg)
            break

    ''' 如果此条SQL是回滚的最后一条SQL,那么就需要更新整个SQL块的状态 '''
    if not s_exec_obj.sql_block.sqlexecdetailmodel_set.filter(sqlrollbackmodel__sql_rollback_result='noexec'):
        try:
            s_exec_obj.sql_block.status = '2'
            s_exec_obj.sql_block.save()
        except:
            pass

''' 获取备份/回滚语句 '''
@shared_task(bind=True,name="SQLBackupSync")
def SQLBackupSync(self,sql_obj):
    ''' 由于执行SQL的 class 是仅执行一个sql_obj,所以这个task要传一个 sql_obj '''
    try:
        db_master_ip = sql_obj.db_name.cluster_name.get(env__exact=sql_obj.env).dbinstancemodel_set.get(role__exact='master').ins_ip.private_ip
    except Exception as e:
        celery_log_error.error("获取 DBModel 对象失败，或者获取 DB 主实例的IP失败,错误信息： %s" % (e.args))
        return

    for sql_exec_obj in sql_obj.sqlexecdetailmodel_set.all():
        ret = {"result": 0}

        if sql_exec_obj.backup_result != 'success':
            ret["result"] = 1
            celery_log_error.error("SQLExecDetailModel 对象 id: %s 备份失败或不需要备份,因此不需要查询备份语句" %(sql_exec_obj.id))
            continue

        inc_back_obj = InceptionApi("", "", "", sql_exec_obj.backup_dbname,sql_str='')

        sql_select_table_name = "SELECT tablename,type from %s.$_$inception_backup_information$_$ WHERE opid_time = '%s'" %(sql_exec_obj.backup_dbname,sql_exec_obj.seqnum)
        print("sql_select_table_name: ",sql_select_table_name)

        ret = inc_back_obj.inception_backup_server(sql_select_table_name)
        if ret['result'] == 1:
            celery_log_error.error("SQLExecDetailModel 对象 id: %s 查询备份表失败,错误信息: %s" %(sql_exec_obj.id,ret["msg"]))
            break
        sql_table_name = ret["backup_select_result"][0][0]
        sql_type_name = ret["backup_select_result"][0][1]

        sql_select_backup_sql = "SELECT rollback_statement  from %s.%s WHERE opid_time = '%s'" %(sql_exec_obj.backup_dbname, sql_table_name,sql_exec_obj.seqnum)

        ret = inc_back_obj.inception_backup_server(sql_select_backup_sql)
        if ret['result'] == 1:
            celery_log_error.error("SQLExecDetailModel 对象 id: %s 获取备份sql失败,错误信息: %s" %(sql_exec_obj.id,ret["msg"]))
            break
        backup_sql_list = ret["backup_select_result"]

        ''' 这里可能会有问题: 更新的行数很多，如10几万行，那么去查找回滚语句并且写回到本地库，如果mysql所在服务器配置不给力的话可能会崩掉 '''
        for backup_sql in backup_sql_list:
            try:
                srb_obj = SQLRollBackModel(**{"sql_rollback":backup_sql[0]})
                inc_obj = InceptionApi("root", "Abcd1234!", db_master_ip, sql_obj.db_name.name, sql_str=backup_sql[0])
                ret = inc_obj.inception_general_check()
                if ret["result"] == 1:
                    celery_log_error.error(ret["msg"])
                    continue
                inc_rollback_result = ret["inc_result"][1]
                srb_obj.sql_already_exec = sql_exec_obj
                srb_obj.rollback_check_affected_rows = inc_rollback_result[6]
                srb_obj.rollback_sql_sha1 = inc_rollback_result[10]
                srb_obj.save()
            except Exception as e:
                celery_log_error.error("SQLRollBackModel 创建对象失败,错误信息: %s" %(e))
                continue

        try:
            sql_exec_obj.sql_tablename = sql_table_name
            sql_exec_obj.sql_type = sql_type_name
            sql_exec_obj.save(update_fields=["sql_tablename","sql_type","last_update_time"])
        except Exception as e:
            celery_log_error.error("SQLExecDetailModel 对象 id: %s 保存备份sql结果失败,错误信息: %s" % (sql_exec_obj.id, e.args))
            break

''' 清空sql语法检查临时表 '''
@shared_task(bind=True,name="ClearSqlCheckTmpTable")
def ClearSqlCheckTmpTable(self):
    SQLCheckTmpModel.objects.all().delete()