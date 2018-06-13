from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic import TemplateView,ListView,View
from dashboard.utils.wslog import wslog_error,wslog_info
import sys
import os
import json
from datetime import *
from django.db.models import Q
from accounts.permission.permission_required_mixin import PermissionRequiredMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from sqlmanager.models import SQLDetailModel,SQLExecDetailModel,DBModel,DBInstanceModel,DBClusterModel,SQLCheckTmpModel,SQLRollBackModel
from django.forms import model_to_dict
from api.thirdapi.inception_api import InceptionApi
from sqlmanager.forms import SQLDetailAddForm
from opsweb.settings import MEDIA_ROOT
from dashboard.utils.get_page_range import get_page_range
from workform.models import WorkFormModel
from sqlmanager.tasks import SQLBackupSync

upload_dir = MEDIA_ROOT + 'sqlfile/'
oneday = timedelta(days=30)
days_30_ago = datetime.now() - oneday

''' Inception 初始化函数 '''
def inception_init_func(sql_block,sql_file_url,db_obj,env,ret):
    if sql_file_url:
        sql_file_dir = upload_dir + sql_file_url
        if not os.path.exists(sql_file_dir):
            ret["result"] = 1
            ret["msg"] = "该文件 '%s'不存在或已被删除..." % (sql_file_dir)
            return ret
        with open(sql_file_dir, 'r') as f:
            sql_detail = f.read()

    try:
        db_master_ip = db_obj.cluster_name.get(env__exact=env).dbinstancemodel_set.get(role__exact='master').ins_ip.private_ip
    except Exception as e:
        ret["result"] = 1
        ret["msg"] = "获取 DBModel 对象失败，或者获取 DB 主实例的IP失败,错误信息： %s" % (e.args)
        return ret

    sql_str = sql_block if sql_block else sql_detail
    inc_obj = InceptionApi("root", "123456", db_master_ip, db_obj.name, sql_str=sql_str)
    ret["inc_obj"] = inc_obj
    ret["db_master_ip"] = db_master_ip
    return ret

''' Inception SQL 语法检查函数 '''
def sql_check_func(sql_block,sql_file_url,db_obj,env,ret):
    ret = inception_init_func(sql_block, sql_file_url, db_obj, env, ret)
    if ret["result"] == 1:
        return ret
    inc_obj =  ret["inc_obj"]
    db_master_ip = ret["db_master_ip"]
    ret = inc_obj.inception_check()
    ret["db_master_ip"] = db_master_ip
    return ret

''' SQL 保存到数据库前需要做的语法检查 '''
class InceptionSqlCheckView(View):
    def post(self,request):
        ret = {"result":0}

        sql_add_form = SQLDetailAddForm(request.POST)
        if not sql_add_form.is_valid():
            ret["result"] = 1
            error_msg = json.loads(sql_add_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([i["message"] for v in error_msg.values() for i in v])
            return JsonResponse(ret)

        sql_block = sql_add_form.cleaned_data.get("sql_block")
        sql_file_url = sql_add_form.cleaned_data.get("sql_file_url")
        db_obj = sql_add_form.cleaned_data.get("db_name")
        env = sql_add_form.cleaned_data.get("env")

        ret = sql_check_func(sql_block, sql_file_url, db_obj, env, ret)

        return JsonResponse(ret)

''' 基于uuid 查看SQL检查结果 '''
class InceptionSqlCheckResultView(ListView):
    template_name = "sql_check_result.html"
    model = SQLCheckTmpModel
    paginate_by = 10
    ordering = '-id'
    page_total = 11

    def get_context_data(self, **kwargs):
        context = super(InceptionSqlCheckResultView, self).get_context_data(**kwargs)
        context['page_range'] = get_page_range(self.page_total, context['page_obj'])
        context["sql_check_uuid"] = self.request.GET.get("sql_check_uuid")
        return context

    # 过滤模型中的数据
    def get_queryset(self):
        queryset = super(InceptionSqlCheckResultView, self).get_queryset()
        sql_check_uuid = self.request.GET.get("sql_check_uuid")
        queryset = SQLCheckTmpModel.objects.filter(sql_check_uuid__exact=sql_check_uuid).values("sql_detail", "affected_rows", "errmsg")
        return queryset

''' 获取SQL拆分结果 '''
class InceptionSqlSplitResultView(ListView):
    template_name = "sql_split_result.html"
    model = SQLExecDetailModel
    paginate_by = 20
    ordering = 'id'
    page_total = 11

    def get_context_data(self, **kwargs):
        context = super(InceptionSqlSplitResultView, self).get_context_data(**kwargs)
        context['page_range'] = get_page_range(self.page_total, context['page_obj'])
        context["id"] = self.request.GET.get("id")
        return context

    # 过滤模型中的数据
    def get_queryset(self):
        queryset = super(InceptionSqlSplitResultView, self).get_queryset()
        id = self.request.GET.get("id")
        queryset = SQLDetailModel.objects.get(id__exact=id).sqlexecdetailmodel_set.values("id","sql", "check_affected_rows")
        return queryset

''' 获取SQL执行结果 '''
class InceptionSqlExecResultView(ListView):
    template_name = "sql_exec_result.html"
    model = SQLExecDetailModel
    paginate_by = 20
    ordering = 'id'
    page_total = 11

    def get_context_data(self, **kwargs):
        context = super(InceptionSqlExecResultView, self).get_context_data(**kwargs)
        context['page_range'] = get_page_range(self.page_total, context['page_obj'])
        s_id = self.request.GET.get("id")
        sql_obj = SQLDetailModel.objects.get(id__exact=s_id)
        sql_exec_failed_id_list = [s.id for s in sql_obj.sqlexecdetailmodel_set.filter(exec_result__exact="failed")]
        if sql_exec_failed_id_list:
            context["sql_exec_failed_id"] = sql_exec_failed_id_list[-1]
        context["s_id"] = s_id
        context["sql_obj"] = sql_obj
        return context

    # 过滤模型中的数据
    def get_queryset(self):
        queryset = super(InceptionSqlExecResultView, self).get_queryset()
        id = self.request.GET.get("id")
        queryset = SQLDetailModel.objects.get(id__exact=id).sqlexecdetailmodel_set.all()
        return queryset

''' SQL保存到数据库 '''
class InceptionSqlAddView(View):
    def post(self,request):
        ret = {"result":0}

        sql_add_form = SQLDetailAddForm(request.POST)
        if not sql_add_form.is_valid():
            ret["result"] = 1
            error_msg = json.loads(sql_add_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([i["message"] for v in error_msg.values() for i in v])
            return JsonResponse(ret)

        sql_check_uuid_list = request.POST.get("sql_check_uuid")
        if sql_check_uuid_list:
            scu_list = sql_check_uuid_list.split(";")
            for scul in scu_list:
                try:
                    SQLCheckTmpModel.objects.filter(sql_check_uuid__exact=scul).delete()
                except:
                    pass

        sd_obj_id_list = []
        if sql_add_form.cleaned_data.get("sql_file_url"):
            sql_file_url_list = sql_add_form.cleaned_data.get("sql_file_url").split(";")
            for sfu  in sql_file_url_list:
                sql_add_form.cleaned_data["sql_file_url"] = sfu
                try:
                    sd_obj = SQLDetailModel(**sql_add_form.cleaned_data)
                    sd_obj.save()
                except Exception as e:
                    ret["result"] = 1
                    ret["msg"] = "保存 SQLDetailModel 对象失败,错误信息： %s" %(e.args)
                    return JsonResponse(ret)
                else:
                    sd_obj_id_list.append(sd_obj.id)
        else:
            try:
                sd_obj = SQLDetailModel(**sql_add_form.cleaned_data)
                sd_obj.save()
            except Exception as e:
                ret["result"] = 1
                ret["msg"] = "保存 SQLDetailModel 对象失败,错误信息： %s" % (e.args)
                return JsonResponse(ret)
            else:
                sd_obj_id_list.append(sd_obj.id)

        ret["msg"] = "保存 SQLDetailModel 对象: %s 成功,可以继续添加SQL或提交工单..." % (sd_obj.id)
        ret["sd_obj_id_list"] = sd_obj_id_list

        return JsonResponse(ret,safe=False)

''' 未处理SQL列表 '''
class InceptionSqlNoexecView(TemplateView):
    template_name = "sql_noexec_list.html"

    def get_context_data(self, **kwargs):
        context = super(InceptionSqlNoexecView, self).get_context_data(**kwargs)

        workform_id = self.request.GET.get("id")

        ''' 判断SQL是来源于 工单还是运维直接操作，如果是来源于工单那么就要等到工单流程到 '运维审批'时才展示 '''
        if workform_id:
            context["sql_no_exec_list"] = SQLDetailModel.objects.filter(sql_workform__process_step__step_id__exact='30').filter(create_time__gte=days_30_ago,sql_workform_id__exact=workform_id).filter(Q(status__exact='0') | Q(status__exact='3'))
        else:
            context["sql_no_exec_list"] = SQLDetailModel.objects.filter(Q(sql_workform__process_step__step_id__exact='30')|Q(sql_workform__isnull=True)).filter(create_time__gte=days_30_ago).filter(Q(status__exact='0') | Q(status__exact='3'))
        return context

''' SQL处理历史列表 '''
class InceptionSqlHistoryView(TemplateView):
    template_name = "sql_history_list.html"

    def get_context_data(self, **kwargs):
        context = super(InceptionSqlHistoryView, self).get_context_data(**kwargs)
        context["sql_exec_history_list"] = SQLDetailModel.objects.filter(create_time__gte=days_30_ago)
        # context["sql_exec_history_list"] = SQLDetailModel.objects.filter(create_time__gte=days_30_ago).exclude(Q(status__exact='0') | Q(status__exact='3'))
        return context

''' 暂停/恢复执行SQL '''
class InceptionSqlPauseView(View):
    def get(self,request):
        ret = {"result":0}

        s_id = request.GET.get("id")
        try:
            s_obj = SQLDetailModel.objects.get(id__exact=s_id)
            s_obj.status = '0' if s_obj.status == '3' else '3'
            s_obj.exec_user = request.user
            s_obj.save(update_fields=["status","exec_user"])
        except SQLDetailModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "SQLDetailModel 不存在 id: %s 的对象，请刷新..." %(s_id)
            return JsonResponse(ret)

        ret["msg"] = "SQLDetailModel id: %s 的对象修改状态成功..." %(s_id)
        return  JsonResponse(ret)

''' 拒绝执行SQL '''
class InceptionSqlRefuseView(View):
    def get(self,request):
        ret = {"result":0}

        s_id = request.GET.get("id")
        try:
            s_obj = SQLDetailModel.objects.get(id__exact=s_id)
            s_obj.status = '4'
            s_obj.exec_user = request.user
            s_obj.save(update_fields=["status","exec_user"])
        except SQLDetailModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "SQLDetailModel 不存在 id: %s 的对象，请刷新..." %(s_id)
            return JsonResponse(ret)

        ret["msg"] = "SQLDetailModel id: %s 的对象修改状态成功..." %(s_id)
        return  JsonResponse(ret)

''' 执行SQL
    这里仅执行一个 sql_obj,即使sql工单包含多个sql_obj,考虑多个sql_obj可能会有依赖关系,因此要单独执行每个sql_obj更灵活些 '''
class InceptionSqlExecView(View):
    def post(self,request):
        ret = {"result":0}

        user_obj = request.user
        s_id = request.POST.get("id")
        s_exec_failed_id = request.POST.get("s_exec_failed_id")
        try:
            s_obj = SQLDetailModel.objects.get(id__exact=s_id)
        except SQLDetailModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "SQLDetailModel 不存在 id: %s 的对象,请刷新..." %(s_id)
            return JsonResponse(ret)

        if s_exec_failed_id:
            sql_exec_list = s_obj.sqlexecdetailmodel_set.filter(id__gt=s_exec_failed_id)
        else:
            sql_exec_list = s_obj.sqlexecdetailmodel_set.all()

        for s in sql_exec_list:
            ret = inception_init_func(s.sql, "", s_obj.db_name, s_obj.env, ret)
            if ret["result"] == 1:
                return JsonResponse(ret)
            inc_obj = ret["inc_obj"]
            db_master_ip = ret["db_master_ip"]
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
            s.sql_sha1 = inc_check_result[10]
            s.execute_time = inc_check_result[9]
            s.backup_dbname = inc_check_result[8]
            if inc_check_result[4] != 'None':
                ret["result"] = 1
                ret["msg"] = "SQLExecDetailModel 模型更新对象id: %s 执行有错误,错误信息: %s" % (s.id, inc_check_result[4])
                try:
                    s.exec_result = "failed"
                    s.backup_result = "noexec"
                    s_obj.exec_status = "1"
                    s.save(update_fields=["errormessage","affected_rows","seqnum","sql_sha1","execute_time","backup_dbname","exec_result","backup_result","last_update_time"])
                    s_obj.save(update_fields=["exec_status","status","exec_user"])
                except Exception as e:
                    wslog_error().error("SQLExecDetailModel 模型更新对象id: %s 失败,错误信息: %s" %(s.id,e.args))
                finally:
                    break

            if inc_check_result[3].split("\n")[0] != 'Execute Successfully':
                ret["result"] = 1
                ret["msg"] = "SQLExecDetailModel 模型更新对象id: %s 执行失败,执行结果: %s" % (s.id,inc_check_result[3].split("\n")[0])
                try:
                    s.exec_result = "failed"
                    s.backup_result = "noexec"
                    s_obj.exec_status = "1"
                    s.save(update_fields=["errormessage","affected_rows","seqnum","sql_sha1","execute_time","backup_dbname","exec_result","backup_result","last_update_time"])
                    s_obj.save(update_fields=["exec_status","status","exec_user"])
                except Exception as e:
                    wslog_error().error("SQLExecDetailModel 模型保存更新对象id: %s 失败,错误信息: %s" % (s.id, e.args))
                finally:
                    break

            try:
                s.backup_result = "failed" if inc_check_result[3].split("\n")[1] != 'Backup successfully' else "success"
                s.exec_result = "success"
                s_obj.exec_status = "0"
                s.save(update_fields=["errormessage","affected_rows","seqnum","sql_sha1","execute_time","backup_dbname","exec_result","backup_result","last_update_time"])
                s_obj.save(update_fields=["exec_status","status","exec_user"])
            except Exception as e:
                ret["result"] = 1
                ret["msg"] = "SQLExecDetailModel 模型保存更新对象id: %s 失败,错误信息: %s" % (s.id, e.args)
                wslog_error().error("SQLExecDetailModel 模型保存更新对象id: %s 失败,错误信息: %s" % (s.id, e.args))
                break

        ''' 后台执行获取备份语句 '''
        SQLBackupSync.delay(s_obj)

        if ret["result"] == 0:
            ret["msg"] = "SQLDetailModel 对象 id: %s 的 所有SQL 执行成功,点击 '确定' 跳转查看执行结果..." %(s_id)

        return JsonResponse(ret)

''' 回滚SQL '''
class InceptionSqlRollBackupView(TemplateView):
    template_name = 'sql_rollback_list.html'

    def get_context_data(self, **kwargs):
        context = super(InceptionSqlRollBackupView,self).get_context_data(**kwargs)
        s_id = self.request.GET.get("id")
        sql_obj = SQLDetailModel.objects.get(id__exact=s_id)
        ''' 过滤掉已经回滚的 sql '''
        context["sql_rollback_list"] = sql_obj.sqlexecdetailmodel_set.filter(sqlrollbackmodel__sql_rollback_result='noexec')
        context["s_id"] = s_id
        return context

    def post(self,request):
        ret = {"result": 0}

        if request.POST.get("s_id"):
            ''' 回滚全部SQL '''
            s_id = request.POST.get("s_id")
            try:
                sql_obj = SQLDetailModel.objects.get(id__exact=s_id)
            except Exception as e:
                ret["result"] = 1
                ret["msg"] = "SQLDetailModel 不存在 id: %s 的对象,请刷新..." %(s_id)
                return JsonResponse(ret)

            sql_obj.status = '2'
            ''' 过滤掉已经回滚的语句 '''
            for s_exec_obj in sql_obj.sqlexecdetailmodel_set.filter(sqlrollbackmodel__sql_rollback_result='noexec'):
                if not s_exec_obj.sqlrollbackmodel.sql_rollback:
                    wslog_error().error("SQLRollBackModel 中不存在 SQLDetailModel 对象 id: %s 的回滚语句，原SQL执行时可能无需备份或者备份失败...")
                    continue
                ret = inception_init_func(s_exec_obj.sqlrollbackmodel.sql_rollback, "", sql_obj.db_name, sql_obj.env, ret)
                if ret["result"] == 1:
                    return JsonResponse(ret)
                inc_obj = ret["inc_obj"]
                db_master_ip = ret["db_master_ip"]
                ret = inc_obj.inception_exec()
                ret["db_master_ip"] = db_master_ip
                if ret["result"] == 1:
                    wslog_error().error(ret["msg"])
                    return JsonResponse(ret)

                inc_rollback_result = ret["inc_result"][1]
                del ret["inc_result"]

                s_exec_obj.sqlrollbackmodel.rollback_exec_user = request.user
                s_exec_obj.sqlrollbackmodel.rollback_errmsg = inc_rollback_result[4]
                s_exec_obj.sqlrollbackmodel.rollback_affected_rows = inc_rollback_result[6]
                '''eval(inc_check_result[7]) 使得 s.seqnum 的值 "'1528168691_434985_2'" 变成 '1528168691_434985_2' '''
                s_exec_obj.sqlrollbackmodel.rollback_seqnum = eval(inc_rollback_result[7])
                s_exec_obj.sqlrollbackmodel.rollback_execute_time = inc_rollback_result[9]
                s_exec_obj.sqlrollbackmodel.rollback_backup_dbname = inc_rollback_result[8]

                if inc_rollback_result[4] != 'None':
                    try:
                        s_exec_obj.sqlrollbackmodel.sql_rollback_result = "failed"
                        sql_obj.exec_status = "1"
                        s_exec_obj.sqlrollbackmodel.save()
                        sql_obj.save(update_fields=["exec_status", "status", "exec_user"])
                    except Exception as e:
                        wslog_error().error("SQLExecDetailModel 模型更新对象 id: %s 失败 \
                                        或者SQLRollBackModel 模型更新对象 id: %s 失败,错误信息: %s" \
                                                % (s_exec_obj.id, s_exec_obj.sqlrollbackmodel.id,e.args))
                    finally:
                        break

                if inc_rollback_result[3].split("\n")[0] != 'Execute Successfully':
                    try:
                        s_exec_obj.sqlrollbackmodel.sql_rollback_result = "failed"
                        sql_obj.exec_status = "1"
                        s_exec_obj.sqlrollbackmodel.save()
                        sql_obj.save(update_fields=["exec_status", "status"])
                    except Exception as e:
                        wslog_error().error("SQLDetailModel 模型更新对象 id: %s 失败 \
                                        或者SQLRollBackModel 模型更新对象 id: %s 失败,错误信息: %s" \
                                                % (sql_obj.id, s_exec_obj.sqlrollbackmodel.id,e.args))
                    finally:
                        break

                try:
                    s_exec_obj.sqlrollbackmodel.sql_rollback_result = "success"
                    sql_obj.exec_status = "0"
                    s_exec_obj.sqlrollbackmodel.save()
                    sql_obj.save(update_fields=["exec_status", "status"])
                except Exception as e:
                    ret["result"] = 1
                    wslog_error().error("SQLDetailModel 模型更新对象 id: %s 失败 \
                                        或者SQLRollBackModel 模型更新对象 id: %s 失败,错误信息: %s" \
                                                % (sql_obj.id, s_exec_obj.sqlrollbackmodel.id,e.args))
                    break
                else:
                    ret["msg"] = "SQL 回滚成功，请查看回滚结果..."

        elif request.POST.get("s_exec_id"):
            ''' 回滚单条SQL '''
            s_exec_id = request.POST.get("s_exec_id")
            try:
                s_exec_obj = SQLExecDetailModel.objects.get(id__exact=s_exec_id)
            except Exception as e:
                ret["result"] = 1
                ret["msg"] = "SQLExecDetailModel 不存在 id: %s 的对象,请刷新..." %(s_exec_id)
                return JsonResponse(ret)

            s_exec_obj.sql_block.status = '5'

            if not s_exec_obj.sqlrollbackmodel.sql_rollback:
                ret["result"] = 1
                ret["msg"] = "SQLRollBackModel 中不存在 SQLDetailModel 对象 id: %s 的回滚语句，原SQL执行时可能无需备份或者备份失败..."
                wslog_error().error("SQLRollBackModel 中不存在 SQLDetailModel 对象 id: %s 的回滚语句，原SQL执行时可能无需备份或者备份失败...")
                return JsonResponse(ret)

            ret = inception_init_func(s_exec_obj.sqlrollbackmodel.sql_rollback, "", s_exec_obj.sql_block.db_name, s_exec_obj.sql_block.env,ret)
            if ret["result"] == 1:
                return JsonResponse(ret)
            inc_obj = ret["inc_obj"]
            db_master_ip = ret["db_master_ip"]
            ret = inc_obj.inception_exec()
            ret["db_master_ip"] = db_master_ip
            if ret["result"] == 1:
                wslog_error().error(ret["msg"])
                return JsonResponse(ret)

            inc_rollback_result = ret["inc_result"][1]
            print("inc_rollback_result: ",inc_rollback_result)
            del ret["inc_result"]

            s_exec_obj.sqlrollbackmodel.rollback_exec_user = request.user
            s_exec_obj.sqlrollbackmodel.rollback_errmsg = inc_rollback_result[4]
            s_exec_obj.sqlrollbackmodel.rollback_affected_rows = inc_rollback_result[6]
            '''eval(inc_check_result[7]) 使得 s.seqnum 的值 "'1528168691_434985_2'" 变成 '1528168691_434985_2' '''
            s_exec_obj.sqlrollbackmodel.rollback_seqnum = eval(inc_rollback_result[7])
            s_exec_obj.sqlrollbackmodel.rollback_execute_time = inc_rollback_result[9]
            s_exec_obj.sqlrollbackmodel.rollback_backup_dbname = inc_rollback_result[8]

            if inc_rollback_result[4] != 'None':
                try:
                    s_exec_obj.sqlrollbackmodel.sql_rollback_result = "failed"
                    s_exec_obj.sqlrollbackmodel.save()
                    s_exec_obj.sql_block.save(update_fields=["status"])
                except Exception as e:
                    ret["result"] = 1
                    ret["msg"] = "SQLExecDetailModel 模型更新对象 id: %s 失败 \
                                或者SQLRollBackModel 模型更新对象 id: %s 失败,错误信息: %s" \
                                    % (s_exec_obj.id, s_exec_obj.sqlrollbackmodel.id, e.args)
                    wslog_error().error("SQLExecDetailModel 模型更新对象 id: %s 失败 \
                                                或者SQLRollBackModel 模型更新对象 id: %s 失败,错误信息: %s" \
                                        % (s_exec_obj.id, s_exec_obj.sqlrollbackmodel.id, e.args))

            if inc_rollback_result[3].split("\n")[0] != 'Execute Successfully':
                try:
                    s_exec_obj.sqlrollbackmodel.sql_rollback_result = "failed"
                    s_exec_obj.sqlrollbackmodel.save()
                    s_exec_obj.sql_block.save(update_fields=["status"])
                except Exception as e:
                    ret["result"] = 1
                    ret["msg"] = "SQLExecDetailModel 模型更新对象 id: %s 失败 \
                                或者SQLRollBackModel 模型更新对象 id: %s 失败,错误信息: %s" \
                                    % (s_exec_obj.id, s_exec_obj.sqlrollbackmodel.id, e.args)
                    wslog_error().error("SQLExecDetailModel 模型更新对象 id: %s 失败 \
                                    或者SQLRollBackModel 模型更新对象 id: %s 失败,错误信息: %s" \
                                        % (s_exec_obj.id, s_exec_obj.sqlrollbackmodel.id, e.args))

            try:
                s_exec_obj.sqlrollbackmodel.sql_rollback_result = "success"
                s_exec_obj.sqlrollbackmodel.save()
                s_exec_obj.sql_block.save(update_fields=["status"])
            except Exception as e:
                ret["result"] = 1
                ret["msg"] = "SQLExecDetailModel 模型更新对象 id: %s 失败 \
                                或者SQLRollBackModel 模型更新对象 id: %s 失败,错误信息: %s" \
                                    % (s_exec_obj.id, s_exec_obj.sqlrollbackmodel.id, e.args)

                wslog_error().error("SQLExecDetailModel 模型更新对象 id: %s 失败 \
                                或者SQLRollBackModel 模型更新对象 id: %s 失败,错误信息: %s" \
                                    % (s_exec_obj.id, s_exec_obj.sqlrollbackmodel.id, e.args))
            else:
                ret["msg"] = "SQL 回滚成功，请查看回滚结果..."

        else:
            ret["result"] = 1
            ret["msg"] = "前端必须传过来一个ID,否则无法知道要回滚哪些SQL,请检查前端配置..."
            return JsonResponse(ret)

        return JsonResponse(ret)

''' 获取SQL回滚结果 '''
class InceptionSqlRollbackResultView(TemplateView):
    template_name = "sql_rollback_result.html"

    def get_context_data(self, **kwargs):
        context = super(InceptionSqlRollbackResultView, self).get_context_data(**kwargs)
        s_id = self.request.GET.get("s_id")
        s_exec_id = self.request.GET.get("s_exec_id")
        if s_id:
            context["sql_rollback_result_list"] = SQLDetailModel.objects.get(id__exact=s_id).sqlexecdetailmodel_set.exclude(sqlrollbackmodel__sql_rollback_result='noexec')
        elif s_exec_id:
            context["sql_rollback_result_list"] = SQLExecDetailModel.objects.filter(id__exact=s_exec_id)
        return context