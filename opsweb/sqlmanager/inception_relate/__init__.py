from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic import TemplateView,ListView,View
from dashboard.utils.wslog import wslog_error,wslog_info
import sys
import os
import re
import json
from datetime import *
from django.db.models import Q
from accounts.permission.permission_required_mixin import PermissionRequiredMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from sqlmanager.models import SQLDetailModel,SQLExecDetailModel,DBModel,DBInstanceModel,DBClusterModel,\
                                SQLCheckTmpModel,SQLRollBackModel,InceptionBackgroundModel,InceptionDangerSQLModel,\
                                STATUS_CHOICES
from django.forms import model_to_dict
from api.thirdapi.inception_api import InceptionApi
from sqlmanager.forms import SQLDetailAddForm,InceptionBackgroundAddForm,InceptionDangerSQLAddForm,InceptionBackgroundChangeForm
from opsweb.settings import MEDIA_ROOT
from dashboard.utils.get_page_range import get_page_range
from workform.models import WorkFormModel
from sqlmanager.tasks import SQLExec

upload_dir = MEDIA_ROOT + 'sqlfile/'
oneday = timedelta(days=30)
days_30_ago = datetime.now() - oneday

''' 判断是不是高危 SQL;感觉很鸡肋，如果多打印几个空格就可屏蔽这个检测 '''
def check_danger_sql(sql, ret):
    danger_sql_list = InceptionDangerSQLModel.objects.filter(status__exact='active')
    ds_str = ''
    for ds in danger_sql_list:
        ds_str += ds.sql_keyword.lower() + '|'

    if not ds_str:
        return ret

    for sql_str in sql.rstrip(';').split(';'):
        if re.search(r"%s" % (ds_str[0:-1]), sql_str.lower().replace("\n",'')):
            ret["result"] = 1
            ret["msg"] = "存在高危SQL: %s" %(sql_str)
            break

    return ret

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

    ''' 检查高危 sql '''
    ret = check_danger_sql(sql_str, ret)

    if ret["result"] == 1:
        return ret

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

''' 回滚SQL公共函数'''
def sql_rollback_func(s_exec_obj,ret,myuser):
    for sr_obj in s_exec_obj.sqlrollbackmodel_set.all():
        ret = inception_init_func(sr_obj.sql_rollback, "", s_exec_obj.sql_block.db_name, s_exec_obj.sql_block.env,ret)
        if ret["result"] == 1:
            break
        inc_obj = ret["inc_obj"]
        db_master_ip = ret["db_master_ip"]
        ret = inc_obj.inception_exec()
        ret["db_master_ip"] = db_master_ip
        if ret["result"] == 1:
            wslog_error().error(ret["msg"])
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

        if inc_rollback_result[4] != 'None':
            try:
                sr_obj.sql_rollback_result = "failed"
                sr_obj.save()
                s_exec_obj.sql_block.save(update_fields=[ "status"])
            except Exception as e:
                err_msg = "SQLExecDetailModel 模型更新对象 id: %s 失败 \
                        或者SQLRollBackModel 模型更新对象 id: %s 失败,错误信息: %s" \
                          % (s_exec_obj.id, sr_obj.id, e.args)
                wslog_error().error(err_msg)
            finally:
                ret["result"] = 1
                ret["msg"] = "执行 SQLRollBackModel 模型对象 id: %s 对应的回滚语句失败,错误信息: %s " % (sr_obj.id, inc_rollback_result[4])
                break

        if inc_rollback_result[3].split("\n")[0] != 'Execute Successfully':
            try:
                s_exec_obj.sqlrollbackmodel.sql_rollback_result = "failed"
                s_exec_obj.sqlrollbackmodel.save()
                s_exec_obj.sql_block.save(update_fields=["status"])
            except Exception as e:
                wslog_error().error("SQLExecDetailModel 模型更新对象 id: %s 失败 \
                                或者SQLRollBackModel 模型更新对象 id: %s 失败,错误信息: %s" \
                                    % (s_exec_obj.id, sr_obj.id, e.args))
            finally:
                ret["result"] = 1
                ret["msg"] = "执行 SQLRollBackModel 模型对象 id: %s 对应的回滚语句失败,错误信息: %s" % (sr_obj.id, inc_rollback_result[3].split("\n")[0])
                break

        try:
            sr_obj.sql_rollback_result = "success"
            sr_obj.save()
            s_exec_obj.sql_block.save(update_fields=["status"])
        except Exception as e:
            err_msg = "SQLExecDetailModel 模型更新对象 id: %s 失败 \
                    或者SQLRollBackModel 模型更新对象 id: %s 失败,错误信息: %s" \
                        % (s_exec_obj.id, sr_obj.id, e.args)
            ret["result"] = 1
            ret["msg"] = err_msg
            wslog_error().error(err_msg)
            break

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
        context["sql_exec_history_list"] = SQLDetailModel.objects.filter(create_time__gte=days_30_ago).order_by("-id")
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

        ''' 这里是根据偏移量获取待执行的sql对象列表，主要是针对一批SQL中出现个别SQL执行报错，但是对后面的SQL没有影响，需要继续执行偏移量之后的SQL... '''
        if s_exec_failed_id:
            sql_exec_list = s_obj.sqlexecdetailmodel_set.filter(id__gt=s_exec_failed_id)
        else:
            sql_exec_list = s_obj.sqlexecdetailmodel_set.all()

        ''' 后台执行SQL '''
        SQLExec.delay(sql_exec_list,s_obj,user_obj,ret)

        return JsonResponse(ret)

''' 回滚SQL '''
class InceptionSqlRollBackupView(TemplateView):
    template_name = 'sql_rollback_list.html'

    def get_context_data(self, **kwargs):
        context = super(InceptionSqlRollBackupView,self).get_context_data(**kwargs)
        s_id = self.request.GET.get("id")
        sql_obj = SQLDetailModel.objects.get(id__exact=s_id)
        ''' 过滤掉已经回滚的 sql '''
        context["sql_rollback_list"] = sql_obj.sqlexecdetailmodel_set.filter(sqlrollbackmodel__sql_rollback_result='noexec').distinct().order_by("-id")
        context["s_id"] = s_id
        return context

    def post(self,request):
        ret = {"result": 0}

        ''' 回滚全部SQL '''
        if request.POST.get("s_id"):
            s_id = request.POST.get("s_id")
            try:
                sql_obj = SQLDetailModel.objects.get(id__exact=s_id)
            except Exception as e:
                ret["result"] = 1
                ret["msg"] = "SQLDetailModel 不存在 id: %s 的对象,请刷新..." %(s_id)
                return JsonResponse(ret)

            sql_obj.status = '2'
            ''' 过滤掉已经回滚的语句;回滚要倒序 '''
            for s_exec_obj in sql_obj.sqlexecdetailmodel_set.filter(sqlrollbackmodel__sql_rollback_result='noexec').distinct().order_by("-id"):
                if not s_exec_obj.sqlrollbackmodel_set.all():
                    wslog_error().error("SQLRollBackModel 中不存在 SQLDetailModel 对象 id: %s 的回滚语句，原SQL执行时可能无需备份或者备份失败...")
                    continue
                ret = sql_rollback_func(s_exec_obj, ret,request.user)

                if ret["result"] == 1:
                    return JsonResponse(ret)

            ret["msg"] = "SQL 回滚成功，请查看回滚结果..."

            ''' 回滚单条SQL '''
        elif request.POST.get("s_exec_id"):
            s_exec_id = request.POST.get("s_exec_id")
            try:
                s_exec_obj = SQLExecDetailModel.objects.get(id__exact=s_exec_id)
            except Exception as e:
                ret["result"] = 1
                ret["msg"] = "SQLExecDetailModel 不存在 id: %s 的对象,请刷新..." %(s_exec_id)
                return JsonResponse(ret)

            s_exec_obj.sql_block.status = '5'

            if not s_exec_obj.sqlrollbackmodel_set.all():
                ret["result"] = 1
                ret["msg"] = "SQLRollBackModel 中不存在 SQLDetailModel 对象 id: %s 的回滚语句，原SQL执行时可能无需备份或者备份失败..."
                wslog_error().error("SQLRollBackModel 中不存在 SQLDetailModel 对象 id: %s 的回滚语句，原SQL执行时可能无需备份或者备份失败...")
                return JsonResponse(ret)

            ret = sql_rollback_func(s_exec_obj, ret,request.user)

            ''' 如果此条SQL是回滚的最后一条SQL,那么就需要更新整个SQL块的状态 '''
            if not s_exec_obj.sql_block.sqlexecdetailmodel_set.filter(sqlrollbackmodel__sql_rollback_result='noexec'):
                try:
                    s_exec_obj.sql_block.status = '2'
                    s_exec_obj.sql_block.save()
                except:
                    pass

            if ret["result"] == 0:
                ret["msg"] = "SQL 回滚成功，请查看回滚结果..."

        else:
            ret["result"] = 1
            ret["msg"] = "前端必须传过来一个ID,否则无法知道要回滚哪些SQL,请检查前端配置..."

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

''' 取消正在使用 osc 执行的alter 语句 '''
class InceptionStopOscView(View):
    def post(self,request):
        ret = {"result": 0}
        s_exec_id = request.POST.get("id")
        try:
            s_exec_obj = SQLExecDetailModel.objects.get(id__exact=s_exec_id)
        except SQLExecDetailModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "SQLExecDetailModel 中不存在 id: %s 的对象，请刷新重试..." %(s_exec_id)
            return JsonResponse(ret)

        inc_obj = InceptionApi("", "", "", "", sql_str="")
        ret = inc_obj.inception_stop_osc(s_exec_obj.sql_sha1)
        print("stop_osc_ret: ",ret)

        return JsonResponse(ret)

''' Inception 后台管理(inception 服务器配置;备份服务器配置) '''
class InceptionBackgroundManageView(TemplateView):
    template_name = "inc_background_manage.html"

    def get_context_data(self, **kwargs):
        context = super(InceptionBackgroundManageView,self).get_context_data(**kwargs)
        context["inc_server_list"] = InceptionBackgroundModel.objects.all()
        context["danger_sql_list"] = InceptionDangerSQLModel.objects.all()
        context["inc_status"] = dict(STATUS_CHOICES)
        return context

    def post(self,request):
        ret = {"result":0}

        inc_bg_form = InceptionBackgroundAddForm(request.POST)
        if not inc_bg_form.is_valid():
            ret['result'] = 1
            error_msg = json.loads(inc_bg_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([i["message"] for v in error_msg.values() for i in v])
            return JsonResponse(ret)

        try:
            inc_bg_obj = InceptionBackgroundModel(**inc_bg_form.cleaned_data)
            inc_bg_obj.save()
        except Exception as e:
            ret['result'] = 1
            ret['msg'] = "Inception 添加服务器 %s 失败,错误信息: %s" % (inc_bg_form.cleaned_data.get('inc_ip'), e.args)
            wslog_error().error("Inception 添加服务器 %s 失败,错误信息: %s" % (inc_bg_form.cleaned_data.get('inc_ip'), e.args))
        else:
            ret['msg'] = "Inception 添加服务器 %s 成功" % (inc_bg_form.cleaned_data.get('name'))

        return JsonResponse(ret)

'''更新 Inception 信息 '''
class InceptionBackgroundManageChangeView(View):
    def get(self,request):
        ret = {"result": 0}
        inc_bg_id = request.GET.get("id")

        try:
            inc_bg_obj = InceptionBackgroundModel.objects.get(id__exact=inc_bg_id)
        except InceptionBackgroundModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "InceptionBackgroundModel 获取对象 id: %s 失败,错误信息: %s" %(inc_bg_id,e.args)

        else:
            ret["inc_bg_info"] = model_to_dict(inc_bg_obj)

        return JsonResponse(ret)

    def post(self,request):
        ret = {"result": 0}
        inc_bg_id = request.POST.get("id")

        inc_bg_form = InceptionBackgroundChangeForm(request.POST)
        if not inc_bg_form.is_valid():
            ret['result'] = 1
            error_msg = json.loads(inc_bg_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([i["message"] for v in error_msg.values() for i in v])
            return JsonResponse(ret)

        try:
            inc_bg_obj = InceptionBackgroundModel.objects.get(id__exact=inc_bg_id)
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "InceptionBackgroundModel 获取对象 id: %s 失败,错误信息: %s" %(inc_bg_id,e.args)
            return JsonResponse(ret)

        inc_ip = inc_bg_form.cleaned_data.get("inc_ip")
        inc_port = request.POST.get("inc_port")
        inc_backup_ip = inc_bg_form.cleaned_data.get("inc_backup_ip")
        inc_backup_port = inc_bg_form.cleaned_data.get("inc_backup_port")
        inc_backup_username = inc_bg_form.cleaned_data.get("inc_backup_username")
        inc_backup_password = inc_bg_form.cleaned_data.get("inc_backup_password")
        inc_status = request.POST.get("inc_status")

        ''' 确保 inc_ip 和 inc_port 是唯一的 '''
        if InceptionBackgroundModel.objects.filter(inc_ip__exact=inc_ip,inc_port__exact=inc_port).exclude(id__exact=inc_bg_id):
            ret["result"] = 1
            ret["msg"] = "InceptionBackgroundModel 中已存在 IP: %s 端口: %s 的对象,请重新修改其他IP或端口..." %(inc_ip,inc_port)
            return JsonResponse(ret)

        ''' 确保 inc_status 仅有一个是处于 active 状态的 '''
        if InceptionBackgroundModel.objects.filter(inc_status__exact=inc_status).exclude(id__exact=inc_bg_id):
            ret["result"] = 1
            ret["msg"] = "Inception 只能存在一个处于 '激活' 状态的服务器..."
            return JsonResponse(ret)

        try:
            inc_bg_obj.inc_ip = inc_ip
            inc_bg_obj.inc_port = inc_port
            inc_bg_obj.inc_backup_ip = inc_backup_ip
            inc_bg_obj.inc_backup_port = inc_backup_port
            inc_bg_obj.inc_backup_username = inc_backup_username
            inc_bg_obj.inc_backup_password = inc_backup_password
            inc_bg_obj.inc_status = inc_status
            inc_bg_obj.save()
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "InceptionBackgroundModel 保存对象 id: %s 的信息失败，错误信息: %s" %(inc_bg_id,e.args)
        else:
            ret["msg"] = "InceptionBackgroundModel 保存对象 id: %s 的信息成功" % (inc_bg_id)

        return JsonResponse(ret)

''' 添加自定义高危SQL '''
class InceptionDangerSQLAddView(View):

    def post(self,request):
        ret = {"result":0}

        inc_ds_form = InceptionDangerSQLAddForm(request.POST)
        if not inc_ds_form.is_valid():
            ret['result'] = 1
            error_msg = json.loads(inc_ds_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([i["message"] for v in error_msg.values() for i in v])
            return JsonResponse(ret)

        try:
            inc_ds_obj = InceptionDangerSQLModel(**inc_ds_form.cleaned_data)
            inc_ds_obj.save()
        except Exception as e:
            ret['result'] = 1
            ret['msg'] = "Inception 自定义高危SQL %s 添加失败,错误信息: %s" % (inc_ds_form.cleaned_data.get("sql_keyword"), e.args)
            wslog_error().error("Inception 自定义高危SQL %s 添加失败,错误信息: %s" % (inc_ds_form.cleaned_data.get("sql_keyword"), e.args))
        else:
            ret['msg'] = "Inception 自定义高危SQL %s 添加成功" % (inc_ds_form.cleaned_data.get("sql_keyword"))

        return JsonResponse(ret)

''' 更新高危SQL信息 '''
class InceptionDangerSQLChangeView(View):
    def get(self,request):
        ret = {"result": 0}
        inc_ds_id = request.GET.get("id")

        try:
            inc_ds_obj = InceptionDangerSQLModel.objects.get(id__exact=inc_ds_id)
        except InceptionDangerSQLModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "InceptionDangerSQLModel 获取对象 id: %s 失败,错误信息: %s" %(inc_ds_id,e.args)
        else:
            ret["inc_ds_info"] = model_to_dict(inc_ds_obj)

        return JsonResponse(ret)

    def post(self,request):
        ret = {"result": 0}
        inc_ds_id = request.POST.get("id")

        inc_ds_form = InceptionDangerSQLAddForm(request.POST)
        if not inc_ds_form.is_valid():
            ret['result'] = 1
            error_msg = json.loads(inc_ds_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([i["message"] for v in error_msg.values() for i in v])
            return JsonResponse(ret)

        try:
            inc_ds_obj = InceptionDangerSQLModel.objects.get(id__exact=inc_ds_id)
            inc_ds_obj.sql_keyword = inc_ds_form.cleaned_data.get("sql_keyword")
            inc_ds_obj.status = inc_ds_form.cleaned_data.get("status")
            inc_ds_obj.save()
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "InceptionDangerSQLModel 获取对象 id: %s 或者保存该对象信息失败,错误信息: %s" %(inc_ds_id,e.args)
        else:
            ret["msg"] = "InceptionDangerSQLModel 保存对象 id: %s 信息成功" %(inc_ds_id)

        return JsonResponse(ret)

''' 删除高危SQL信息 '''
class InceptionDangerSQLDeleteView(View):
    def post(self,request):
        ret = {"result": 0}
        inc_ds_id = request.POST.get("id")

        try:
            inc_ds_obj = InceptionDangerSQLModel.objects.get(id__exact=inc_ds_id)
            inc_ds_obj.delete()
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "InceptionDangerSQLModel 删除对象 id: %s 失败,错误信息: %s" %(inc_ds_id,e.args)
        else:
            ret["msg"] = "InceptionDangerSQLModel 删除对象 id: %s 成功" % (inc_ds_id)
        return JsonResponse(ret)