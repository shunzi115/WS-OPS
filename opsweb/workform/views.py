from django.shortcuts import render,reverse
from django.http import HttpResponse,JsonResponse,StreamingHttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View,TemplateView,ListView
from accounts.permission.permission_required_mixin import PermissionRequiredMixin
from dashboard.utils.wslog import wslog_error,wslog_info
from workform.models import WorkFormModel,ProcessModel,ApprovalFormModel,WorkFormTypeModel,WorkFormBaseModel
from opsweb.settings import MEDIA_ROOT
from datetime import datetime
import os
import json
from workform.forms import PubWorkFormAddForm,WorkFormApprovalForm,SqlWorkFormAddForm,OthersWorkFormAddForm
from django.db.models import Q
from django.contrib.auth.models import User,Group
from dashboard.utils.utc_to_local import utc_to_local
from dashboard.utils.ws_mail_send import mail_send
from workform.tasks import workform_mail_send
import time

''' 添加 发布工单 '''
class PubWorkFormAddView(LoginRequiredMixin,PermissionRequiredMixin,TemplateView):
    permission_required = "workform.add_workformmodel"
    permission_redirect_url = "workform_list"
    
    template_name = "pub_workform_add.html"

    def get_context_data(self,**kwargs):
        context = super(PubWorkFormAddView,self).get_context_data(**kwargs)
        context["sql"] = dict(WorkFormModel.SQL_CHOICES)
        context["level"] = dict(WorkFormModel.LEVEL_CHOICES)
        context["reason"] = dict(WorkFormModel.REASON_CHOICES)
        return context

''' 添加 SQL工单 '''
class SqlWorkFormAddView(LoginRequiredMixin,PermissionRequiredMixin,TemplateView):
    permission_required = "workform.add_workformmodel"
    permission_redirect_url = "workform_list"

    template_name = "sql_workform_add.html"

    def get_context_data(self,**kwargs):
        context = super(SqlWorkFormAddView,self).get_context_data(**kwargs)
        context["level"] = dict(WorkFormModel.LEVEL_CHOICES)
        context["reason"] = dict(WorkFormModel.REASON_CHOICES)
        return context

''' 添加 其他运维工单 '''
class OthersWorkFormAddView(LoginRequiredMixin,PermissionRequiredMixin,TemplateView):
    permission_required = ("workform.add_workformmodel","workform.add_others_workform")
    permission_redirect_url = "workform_list"

    ''' 以逻辑 '或' 的关系判断上面的权限要求 '''
    def has_permission(self):
        return [perm for perm in self.permission_required if self.request.user.has_perm(perm)]

    template_name = "others_workform_add.html"

    def get_context_data(self,**kwargs):
        context = super(OthersWorkFormAddView,self).get_context_data(**kwargs)
        context["level"] = dict(WorkFormModel.LEVEL_CHOICES)
        context["type_list"] = dict(WorkFormTypeModel.objects.exclude(Q(name__exact="publish")|Q(name__exact="rollback")|Q(name__exact="sql_exec")).values_list("name","cn_name"))
        return context

''' 工单信息提交 '''
class WorkFormAddBaseView(LoginRequiredMixin,View):
    permission_required = ("workform.add_workformmodel","workform.add_others_workform")

    ''' 根据ProcessModel 字段 approval_require 定义的 '标记' 获取每一个 step 的审核人列表 '''
    def get_approver_can(self,user_obj,approval_require,ret):

        ''' 针对审核要求是组的情况，定义下面这个字典-{"审核人的标记": "组名"}'''
        approval_require_dict = {"2":"qa","3":"ops","6":"ws-trade","7":"ws-item","8":"ws-user"}

        user_obj_list = []

        if approval_require in ["2","3","6","7","8"] :
            ''' 对审核要求为组的情况,做统一处理'''
            try:
                user_obj_list = list(Group.objects.get(name__exact=approval_require_dict.get(approval_require,"ops")).user_set.exclude(id__exact=user_obj.id))
            except Exception as e:
                ret["result"] = 1
                ret["msg"] = "获取 %s 组内可以审核的用户对象失败,请联系运维人员" %(approval_require_dict.get(approval_require,"ops"))
                wslog_error().error("获取 %s 组内可以审核的用户对象失败,错误信息: %s" %(approval_require_dict.get(approval_require,"ops"),e.args))
            else:
                ret["user_obj_list"] = user_obj_list

        elif approval_require == '1' :
            ''' 用户所属组内的 leader 审核 '''
            try:
                for group_obj in user_obj.groups.all() :
                    user_obj_list += list(group_obj.user_set.exclude(id__exact=user_obj.id))
            except Exception as e:
                ret["result"] = 1
                ret["msg"] = "获取可以审核的用户对象失败,请联系运维人员"
                wslog_error().error("获取可以审核的用户对象失败,错误信息: %s" %(e.args))
            else: 
                ret["user_obj_list"] = user_obj_list

        elif approval_require == "4" or approval_require == "9":
            ''' 用户自己审核或者不需要审核 '''
            user_obj_list.append(user_obj)
            ret["user_obj_list"] = user_obj_list
 
        else:
            ret["result"] = 1
            ret["msg"] = "此流程步骤所需的审核组或用户: %s 未配置,请联系运维进行配置" %(approval_require)
            wslog_error().error("此流程步骤: %s 未配置相应的审核组或用户,请进行配置" %(approval_require))

        return ret

    def post(self,request):
        time_begin = int(round(time.time() * 1000))
        ret = {"result":0,"msg":"success"}
        user_cn_name = request.user.userextend.cn_name

        ## ajax 请求的权限验证
        if not [ perm for perm in self.permission_required if request.user.has_perm(perm)]:
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有'添加 workform 模型对象'的权限,请联系运维!"
            return JsonResponse(ret)  

        workform_type = request.POST.get("type",None)
        if not workform_type:
            ret["result"] = 1
            ret["msg"] = "工单必须选择一个类型"
            return JsonResponse(ret)

        ''' 通过工单类型来查询此工单的审核流程 '''
        try:
            wft_obj = WorkFormTypeModel.objects.get(name__exact=workform_type)
        except WorkFormTypeModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "该工单类型:'%s' 在模型 WorkFormTypeModel 中不存在,请联系运维人员" %(workform_type)
            wslog_error().error("用户: %s 添加工单,该工单类型:'%s' 在模型 WorkFormTypeModel 中不存在,请检查" %(user_cn_name,workform_type))
            return JsonResponse(ret)
        else:
            process_step_list = wft_obj.process_step_id.split(" -> ")

        ''' 根据工单类型选择相应的 验证form '''
        if workform_type in ["publish","rollback"]:
            workform_add_form = PubWorkFormAddForm(request.POST)
        elif workform_type == "sql_exec":
            workform_add_form = SqlWorkFormAddForm(request.POST)
        else:
            workform_add_form = OthersWorkFormAddForm(request.POST)

        if not workform_add_form.is_valid():
            ret["result"] = 1
            error_msg = json.loads(workform_add_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([ i["message"] for v in error_msg.values() for i in v ])
            return JsonResponse(ret) 
        
        ''' 创建一个 WorkFormModel 对象,并关联上待执行的流程 step '''
        try:
            p_obj = ProcessModel.objects.get(step_id__exact=process_step_list[0])
            workform_obj = WorkFormModel(**workform_add_form.cleaned_data)
            workform_obj.applicant = request.user
            workform_obj.type = wft_obj
            workform_obj.process_step = p_obj
            workform_obj.save()
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "WorkFormModel 模型对象保存失败,错误信息: %s" %(e.args)
            wslog_error().error("用户: %s 添加 WorkFormModel 模型对象 '%s' 保存失败,错误信息: %s" %(user_cn_name,workform_add_form.cleaned_data.get("title"),e.args))
            return JsonResponse(ret)

        ''' 循环该工单的流程 step,建立 ProcessModel 中 step 与 ApprovalFormModel 的关联 '''
        for process_step in process_step_list:
            try:
                process_obj = ProcessModel.objects.get(step_id__exact=process_step)
            except ProcessModel.DoesNotExist:
                ret["result"] = 1
                ret["msg"] = "ProcessModel 模型不存在 step_id 为 %s 的对象,请联系运维人员" %(process_step)
                wslog_error().error("用户: %s 添加工单: '%s' 中 ProcessModel 模型不存在 step_id 为 %s 的对象" %(user_cn_name,workform_obj.title,process_step))
                workform_obj.delete()
                break

            ret = self.get_approver_can(request.user,process_obj.approval_require,ret)

            if ret["result"] == 1:
                workform_obj.delete()
                break

            af_obj = ApprovalFormModel()
            try:
                af_obj.workform = workform_obj
                af_obj.process = process_obj
                af_obj.save()
            except Exception as e:
                ret["result"] = 1
                del ret["user_obj_list"]
                ret["msg"] = "ApprovalFormModel 模型保存对象失败,请联系运维人员"
                wslog_error().error("用户: %s 添加工单: '%s' 中 ApprovalFormModel 模型保存对象失败,错误信息: %s" %(user_cn_name,workform_obj.title,e.args))
                workform_obj.delete()
                break

            if ret["user_obj_list"]:
                af_obj.approver_can.set(ret["user_obj_list"])
                del ret["user_obj_list"]
            else:
                ret["result"] = 1
                ret["msg"] = "该流程步骤 %s 未查到可审核的用户对象列表,请联系运维人员" %(process_step)
                workform_obj.delete()
                break

        if ret["result"] == 1:
            return JsonResponse(ret)
        
        ''' 
            根据ApprovalFormModel中的approver_can字段关联的User对象,来生成WorkFormModel中 approver_can字段 与User对象的多对多关系,
            相当于 复制了ApprovalFormModel中的approver_can字段
        '''
        try:
            workform_obj.approver_can.set(workform_obj.approvalformmodel_set.get(process_id__exact=workform_obj.process_step_id).approver_can.all())
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "根据模型ApprovalFormModel的字段approver_can来生成模型WorkFormModel字段approver_can与User多对多关系失败"
            wslog_error().error("根据模型ApprovalFormModel的字段approver_can来生成模型WorkFormModel字段approver_can与User多对多关系失败")
            workform_obj.delete()
        else:
            ret["msg"] = "发布工单: '%s' 创建成功" %(workform_add_form.cleaned_data.get("title"))
            wslog_info().info("用户: %s 发布工单: '%s' 创建成功" %(user_cn_name,workform_obj.title))
            approver_can_email_list = [i["email"] for i in workform_obj.approver_can.values("email")]
            email_subject = '[%s]:%s' %(workform_obj.type.cn_name,workform_obj.title)
            email_content = '''<p>有工单需要你<strong style="color:red"> 审批/验证/执行</strong>,请前往运维平台操作</p>
                            <p>工单主题: <strong style="color:blue">%s</strong></p>
                            <p>工单流程StepID: <strong style="color:blue">%s</strong></p>
                            <p>URL链接: <a href="http://%s" target="_blank">点击跳转</a></p>''' %(workform_obj.title,
                                                                                            workform_obj.process_step.step,
                                                                                            request.get_host() + reverse("my_workform_list"))
            #mail_send(email_subject,email_content,["15018446704@163.com","172250732@qq.com"],html_content=email_content)
            try:
                workform_mail_send.delay(email_subject,"hahahaahaha",["15018446704@163.com","172250732@qq.com"],html_content=email_content)
            except Exception as e:
                pass
        time_end = int(round(time.time() * 1000))
        time_spend = time_end - time_begin
        print("time_spend: ",time_spend)
        return JsonResponse(ret)


''' 工单列表 '''
class WorkFormListView(LoginRequiredMixin,ListView):
    template_name = "workform_list.html"
    model = WorkFormModel
    paginate_by = 10
    ordering = '-id'
    page_total = 11

    def get_context_data(self,**kwargs):
        context = super(WorkFormListView,self).get_context_data(**kwargs)
        context['page_range'] = self.get_page_range(context['page_obj'])
        context['level_range'] = range(0,len(WorkFormBaseModel.LEVEL_CHOICES))
        context['approval_result'] = dict(ApprovalFormModel.RESULT_CHOICES)
        # request.GET 是获取QueryDict对象,也即是前端传过来的所有参数,由于QueryDict对象是只读的,所有要使用copy方法,赋值一份出来,才能进行修改
        search_data = self.request.GET.copy()
        try:
            search_data.pop('page')
        except:
            pass

        if search_data:
            context['search_uri'] = '&' + search_data.urlencode()
        else:
            context['search_uri'] = '' 
        # context.update(字典A) 是合并字典 context 和 A
        context.update(search_data.dict())
        return context

    # 过滤模型中的数据
    def get_queryset(self):
        queryset = super(WorkFormListView,self).get_queryset()

        search_name = self.request.GET.get('search',None)
        if search_name:
            queryset = queryset.filter(Q(title__icontains=search_name)|Q(detail__icontains=search_name)|Q(module_name__icontains=search_name))
        return queryset
    
    # 获取要展示的页数范围,这里是固定显示多少页
    def get_page_range(self,page_obj):
        page_now = page_obj.number
        if page_obj.paginator.num_pages > self.page_total:
            page_start = page_now - self.page_total//2
            page_end = page_now + self.page_total//2 + 1

            if page_start <= 0:
                page_start = 1
                page_end = page_start + self.page_total
            if page_end > page_obj.paginator.num_pages:
                page_end = page_obj.paginator.num_pages + 1
                page_start = page_end - self.page_total
        else:
            page_start = 1
            page_end = page_obj.paginator.num_pages + 1

        page_range = range(page_start,page_end)
        return page_range

''' 我的工单列表: 我发出的工单/我待审批的工单/我审批过的工单 '''
class MyWorkFormListView(WorkFormListView):
    template_name = "my_workform_list.html"
    ordering = "-id"

    def get_context_data(self,**kwargs):
        context = super(MyWorkFormListView,self).get_context_data(**kwargs)
        ''' 我审核过的工单 '''
        context["approvaled_workform_list"] = WorkFormModel.objects.filter(approvalformmodel__approver__username__exact=self.request.user.username).exclude(applicant__username__exact=self.request.user.username).distinct()

        return context

    def get_queryset(self):
        queryset = super(MyWorkFormListView,self).get_queryset()
        ''' 我发出或我可以审核的工单 '''
        queryset = WorkFormModel.objects.filter(Q(applicant__username__exact=self.request.user.username)|Q(approver_can__username__exact=self.request.user.username)).distinct()

        search_name = self.request.GET.get('search',None)
        if search_name:
            queryset = queryset.filter(Q(title__icontains=search_name)|Q(detail__icontains=search_name)|Q(module_name__icontains=search_name)).distinct()
        return queryset

''' 审批工单 '''
class ApprovalWorkFormView(LoginRequiredMixin,View):
    permission_required = "workform.change_workformmodel"

    def get(self,request):
        ret = {"result":0}

        ## ajax 请求的权限验证
        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有'审批工单'的权限,请联系运维!"
            return JsonResponse(ret) 

        wf_id = request.GET.get("id")
        process_step_id = request.GET.get("process_id")

        try:
            wf_obj = WorkFormModel.objects.get(id__exact=wf_id)
        except WorkFormModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "WorkFormModel 模型不存在 id: %s 的对象,请刷新重试..." %(wf_id)
            wslog_error().error("WorkFormModel 模型不存在 id: %s 的对象" %(wf_id))
            return JsonResponse(ret)

        try:
            wf_info = WorkFormModel.objects.filter(id__exact=wf_id).values("id","title","detail","applicant","module_name")[0]
            wf_info["level"] = wf_obj.get_level_display()
            wf_info["process"] = wf_obj.process_step.step
            wf_info["type_id"] = wf_obj.type.cn_name
            wf_info["type"] = wf_obj.type.name
            wf_info["applicant"] = wf_obj.applicant.userextend.cn_name
            wf_info["status"] = wf_obj.get_status_display()
            wf_info["process_step_id"] = process_step_id
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "WorkFormModel 模型 id: %s 的对象转 dict 失败,请查看日志..." %(wf_id)
            wslog_error().error("WorkFormModel 模型 id: %s 的对象转 dict 失败,错误信息: %s" %(wf_id,e.args))
        else:
            wslog_info().info("WorkFormModel 模型 id: %s 的对象转 dict 成功,查询该对象的详情成功" %(wf_id))
            ret["wf_info"] = wf_info
        return JsonResponse(ret)

    def post(self,request):
        ret = {"result":0}

        ## ajax 请求的权限验证
        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有'审批工单'的权限,请联系运维!"
            return JsonResponse(ret) 

        wf_id = request.POST.get("id")
        process_step_id = request.POST.get("process_step_id")

        workform_approval_form = WorkFormApprovalForm(request.POST)

        if not workform_approval_form.is_valid():
            ret["result"] = 1
            error_msg = json.loads(workform_approval_form.errors.as_json(escape_html=False)) 
            ret["msg"] = '\n'.join([ i["message"] for v in error_msg.values() for i in v ])
            return JsonResponse(ret)

        if not wf_id or not process_step_id:
            ret["result"] = 1
            ret["msg"] = "未从前端接收到工单id 或 流程step id 信息,请刷新重试..." 
            return JsonResponse(ret)
        else:
            process_step_id = int(process_step_id)

        try:
            wf_obj = WorkFormModel.objects.get(id__exact=wf_id)
        except WorkFormModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "WorkFormModel 模型不存在 id: %s 的对象,请刷新重试..." %(wf_id)
            wslog_error().error("WorkFormModel 模型不存在 id: %s 的对象" %(wf_id))
            return JsonResponse(ret)

        if int(process_step_id) != wf_obj.process_step_id:
            ret["result"] = 1
            ret["msg"] = "审批失败，因为 WorkFormModel 模型对象 id: %s 流程进度已发生了变化,请刷新..." %(wf_id)
            wslog_error().error("用户 %s 审批失败,WorkFormModel模型对象id: %s 流程进度已不是提交时的进度: process_step_id 为 %s" %(request.user.username,wf_id,process_step_id))
            return JsonResponse(ret)

        if request.user not in wf_obj.approver_can.all():
            ret["result"] = 1
            ret["msg"] = "审批失败，你没有权限审核 WorkFormModel 模型对象 id: %s 流程进度: %s 的工单" %(wf_id,process_step_id)    
            wslog_error().error("用户 %s 审批失败,你没有权限审核 WorkFormModel 模型对象 id: %s 流程进度: %s 的工单" %(request.user.username,wf_id,process_step_id)) 
            return JsonResponse(ret)

        try:
            af_obj = ApprovalFormModel.objects.get(workform_id__exact=wf_id,process_id=process_step_id)
            af_obj.approver = request.user
            af_obj.result = workform_approval_form.cleaned_data.get("result")
            af_obj.approve_note = workform_approval_form.cleaned_data.get("approve_note")
            af_obj.approval_time = datetime.now().strftime("%Y-%m-%d %X")
            af_obj.save(update_fields=["approver","result","approve_note","approval_time"])   
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "审批失败，更新 ApprovalFormModel 模型对象 workform_id: %s 流程进度: %s 的工单 审批信息失败,请联系运维同事" %(wf_id,process_step_id)
            wslog_error().error("用户 %s 审批失败,更新 ApprovalFormModel 模型对象 workform_id: %s 流程进度: %s 的工单 审批信息失败,错误信息: %s" %(request.user.username,wf_id,process_step_id,e.args))
            return JsonResponse(ret)
        
        ''' 查询并确定流程下一个 step_id '''
        wf_process_list = list(wf_obj.approvalformmodel_set.filter(id__gt=af_obj.id).values("id","process_id").order_by("id"))

        if not wf_process_list:
            ret["result"] = 1
            ret["msg"] = "WorkFormModel 模型对象 id: %s 的工单已经流程审批结束,不能再次审批" %(wf_id)
            wslog_error().error("用户 %s 审批失败,WorkFormModel 模型对象 id: %s 的工单已经流程审批结束,不能再次审批" %(request.user.username,wf_id))
            return JsonResponse(ret)

        process_next_id = wf_process_list[0]["process_id"]

        try:
            p_obj = ProcessModel.objects.get(id__exact=process_next_id)
        except ProcessModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "ProcessModel 模型中不存在 id: %s 的 step,请联系运维检查..." %(process_next_id)
            return Jsonresponse(ret)
        else:
            next_step_id = p_obj.step_id

        ''' 更新工单的状态 '''
        if af_obj.result == "0" and next_step_id == 60:
            ''' 如果工单审批通过且下一个流程step是'完成',则设置工单状态为'完成',工单流程审批/执行'完成',同时清空可审核人 '''
            wf_obj.status = "2"
            wf_obj.process_step_id = process_next_id
            wf_obj.complete_time = datetime.now().strftime("%Y-%m-%d %X")
            wf_obj.approver_can.clear()
            try:
                ''' 设置ApprovalFormModel中 step 为'完成'的审核结果为'通过' 方便 流程跟踪 中状态的获取 '''
                next_af_obj = wf_obj.approvalformmodel_set.get(process_id__exact=process_next_id)
                next_af_obj.result = "0"
                next_af_obj.approval_time = datetime.now().strftime("%Y-%m-%d %X")
                next_af_obj.save(update_fields=["result","approval_time"])
            except Exception as e:
                ret["result"] = 1
                ret["msg"] = "ApprovalFormModel 模型自动添加 step 为'完成' 时的审核结果失败"
                wslog_error().error("ApprovalFormModel 模型自动添加 step 为'完成' 时的审核结果失败,错误信息: %s" %(e.args))
                return Jsonresponse(ret)
            else:
                approver_can_email_list = [request.user.email]
                email_content = '''<p>你的工单<strong style="color:red">完成</strong>，如有需要请前往运维平台查看</p>
                            <p>工单主题: <strong style="color:blue">%s</strong></p>
                            <p>URL链接: <a href="http://%s" target="_blank">点击跳转</a></p>''' %(wf_obj.title,
                                                                                            request.get_host() + ':9999' + reverse("my_workform_list"))

        elif  af_obj.result == "2" or af_obj.result == "3":
            ''' 如果工单当前流程step的审核结果是'暂停'或'有异常', 则更新工单的状态为'暂停',同时工单的流程step不变,可审核人变成当前审核的人 '''
            wf_obj.status = "3"
            wf_obj.approver_can.set([request.user])
            approver_can_email_list = [wf_obj.applicant.email]
            email_content = '''<p>有工单需要你<strong style="color:red"> 审批/验证/执行</strong>，请前往运维平台操作</p>
                            <p>工单主题: <strong style="color:blue">%s</strong></p>
                            <p>审批说明: 你的工单在流程 '%s' 被审批为 <strong style="color:red">%s</strong> 请联系 审批人 '%s' </p>
                            <p>URL链接: <a href="http://%s" target="_blank">点击跳转</a></p>''' %(wf_obj.title,
                                                                                            wf_obj.process_step.step,
                                                                                            af_obj.get_result_display(),
                                                                                            request.user.userextend.cn_name,
                                                                                            request.get_host() + reverse("my_workform_list"))
        elif af_obj.result == "1":
            ''' 如果工单当前流程step的审核结果是'拒绝',就把工单状态变为'完成',同时审批流程也结束 '''
            wf_obj.status = "2"
            wf_obj.complete_time = datetime.now().strftime("%Y-%m-%d %X")
            wf_obj.approver_can.clear()
            approver_can_email_list = [wf_obj.applicant.email]
            email_content = '''<p>有工单需要你<strong style="color:red"> 审批/验证/执行</strong>，请前往运维平台操作</p>
                            <p>工单主题: <strong style="color:blue">%s</strong></p>
                            <p>审批说明: 你的工单在流程 '%s' 被审批为 <strong style="color:red">%s</strong> 请联系 审批人 '%s' </p>
                            <p>URL链接: <a href="http://%s" target="_blank">点击跳转</a></p>''' %(wf_obj.title,
                                                                                            wf_obj.process_step.step,
                                                                                            af_obj.get_result_display(),
                                                                                            request.user.userextend.cn_name,
                                                                                            request.get_host() + reverse("my_workform_list"))
        else:
            wf_obj.status = "1"
            wf_obj.process_step_id = process_next_id
            wf_obj.approver_can.set(ApprovalFormModel.objects.get(workform_id__exact=wf_id,process_id=process_next_id).approver_can.all())
            approver_can_email_list = [i["email"] for i in wf_obj.approver_can.values("email")]
            email_content = '''<p>有工单需要你<strong style="color:red"> 审批/验证/执行</strong>，请前往运维平台操作</p>
                            <p>工单主题: <strong style="color:blue">%s</strong></p>
                            <p>工单流程StepID: <strong style="color:blue">%s</strong></p>
                            <p>URL链接: <a href="http://%s" target="_blank">点击跳转</a></p>''' %(wf_obj.title,
                                                                                            wf_obj.process_step.step,
                                                                                            request.get_host() + reverse("my_workform_list"))

        try:
            wf_obj.save(update_fields=["status","process_step_id","complete_time"])
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "审批失败，更新 WorkFormModel 模型对象 id: %s 的工单为最新的流程进度: %s 出现异常,请联系运维同事" %(wf_id,process_next_id)
            wslog_error().error("用户 %s 审批失败,更新 WorkFormModel 模型对象 id: %s 的工单为最新的流程进度: %s 出现异常,错误信息: %s" %(request.user.username,wf_id,process_next_id,e.args))
            return JsonResponse(ret)

        ret["msg"] = "更新 WorkFormModel 模型对象 id: %s 的工单为最新的流程进度: %s 成功" %(wf_id,process_next_id)
        wslog_info().info("用户 %s 更新 WorkFormModel 模型对象 id: %s 的工单为最新的流程进度: %s 成功" %(request.user.username,wf_id,process_next_id))
        email_subject = '[%s]:%s' %(wf_obj.type.cn_name,wf_obj.title)
        mail_send(email_subject,email_content,approver_can_email_list,html_content=email_content)
        try:
            workform_mail_send.delay(email_subject, "hahahaahaha", ["15018446704@163.com", "172250732@qq.com"],html_content=email_content)
        except Exception as e:
            pass
        return JsonResponse(ret)

''' 工单信息查询 '''
class WorkFormInfoView(LoginRequiredMixin,View):

    def get(self,request):

        ret = {"result":0}
        wf_id = request.GET.get("id")

        try:
            wf_obj = WorkFormModel.objects.get(id__exact=wf_id)
        except WorkFormModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "WorkFormModel 模型不存在 id: %s 的对象,请刷新重试..." %(wf_id)
            wslog_error().error("WorkFormModel 模型不存在 id: %s 的对象" %(wf_id))
            return JsonResponse(ret)

        try:
            wf_info = WorkFormModel.objects.filter(id__exact=wf_id).values()[0]
            wf_info["level"] = wf_obj.get_level_display()
            wf_info["status"] = wf_obj.get_status_display()
            wf_info["type_id"] = wf_obj.type.cn_name
            wf_info["type"] = wf_obj.type.name
            wf_info["applicant"] = wf_obj.applicant.userextend.cn_name
            if wf_info.get("create_time"):
                wf_info["create_time"] = wf_obj.create_time
            if wf_info.get("complete_time"):
                wf_info["complete_time"] = wf_obj.complete_time
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "WorkFormModel 模型 id: %s 的对象转 dict 失败,请查看日志..." %(wf_id)
            wslog_error().error("WorkFormModel 模型 id: %s 的对象转 dict 失败,错误信息: %s" %(wf_id,e.args))
        else:
            wslog_info().info("WorkFormModel 模型 id: %s 的对象转 dict 成功,查询该对象的详情成功" %(wf_id))
            ret["wf_info"] = wf_info

        return JsonResponse(ret)

''' 流程跟踪 '''
class ProcessTraceView(LoginRequiredMixin,View):
    def post(self,request):
        ret = {"result":0}

        w_id = request.POST.get("id")

        try:
            w_obj = WorkFormModel.objects.get(id__exact=w_id)
        except WorkFormModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "WorkFormModel 模型不存在 id: %s 的对象,请刷新重试" %(w_id)
            wslog_error().error("WorkFormModel 模型不存在 id: %s 的对象,请刷新重试" %(w_id))
            return JsonResponse(ret)

        process_list = []
        for i in w_obj.approvalformmodel_set.order_by("id"):
            process = {}
            if i.result and i.process.step_id !=60:
                process["approver"] = i.approver.userextend.cn_name
                process["result"] = i.get_result_display()
                process["approve_note"] = i.approve_note
                process["id"] = i.id
                process["process"] = i.process.step
                process["process_step_id"] = i.process.step_id
                process["approve_time"] = i.approval_time
            else:
                process["id"] = i.id
                process["result"] = i.get_result_display()
                process["process"] = i.process.step
                process["process_step_id"] = i.process.step_id
            process_list.append(process)

        ret["process_list"] = process_list

        return JsonResponse(ret)

''' 工单审批流程每一个步骤的审核结果 '''
class ProcessStepApprovalInfoView(LoginRequiredMixin,View):
    def get(self,request):
        ret = {"result":0}

        id = request.GET.get("id")

        try:
            af_obj = ApprovalFormModel.objects.get(id__exact=id)
        except ApprovalFormModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "ApprovalFormModel 模型不存在 id: %s 的对象,请刷新重试" %(id)
            wslog_error().error("ApprovalFormModel 模型不存在 id: %s 的对象" %(id))
            return JsonResponse(ret)

        approval_info = {}

        if not af_obj.result:
            ret["result"] = 1
            ret["msg"] = "ApprovalFormModel 模型 id: %s 的对象,还未审批,因此查不到审批结果" %(id)
            wslog_error().error("ApprovalFormModel 模型存在 id: %s 的对象,还未审批,因此查不到审批结果" %(id))
            return JsonResponse(ret)

        approval_info["approver"] = af_obj.approver.userextend.cn_name
        approval_info["result"] = af_obj.get_result_display()
        approval_info["approve_note"] = af_obj.approve_note
        approval_info["process"] = af_obj.process.step
        approval_info["approve_time"] = af_obj.approval_time
        ret["approval_info"] = approval_info

        return JsonResponse(ret)

''' 工单删除 '''
class WorkFormDeleteView(LoginRequiredMixin,View): 
    permission_required = "workform.delete_workformmodel"

    def post(self,request):
        ret = {"result":0}
        id = request.POST.get("id")

        ## ajax 请求的权限验证
        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有'删除工单'的权限,请联系运维!"
            return JsonResponse(ret)

        try:
            w_obj = WorkFormModel.objects.get(id__exact=id)
        except WorkFormModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "WorkFormModel 模型不存在 id: %s 的对象,请刷新重试" %(id)
            wslog_error().error("用户: %s 删除 WorkFormModel 模型 id: %s 的对象失败" %(request.user.username,id))
            return JsonResponse(ret)
        
        if request.user.is_superuser == 1 or (request.user == w_obj.applicant and  w_obj.status == "0"):
            try:
                w_obj.delete()
            except Exception as e:
                ret["result"] = 1
                ret["msg"] = "WorkFormModel 模型 id: %s 的对象删除失败,请联系运维同事查看日志" %(id)
                wslog_error().error("用户: %s 删除 WorkFormModel 模型 id: %s 的对象失败,错误信息: %s" %(request.user.username,id,e.args))
            else:
                ret["msg"] = "WorkFormModel 模型 id: %s 的对象删除成功" %(id)
                wslog_info().info("用户: %s 删除 WorkFormModel 模型 id: %s 的对象成功" %(request.user.username,id))
        else:
            ret["result"] = 1
            ret["msg"] = "只有管理员或者(工单状态的发布者及工单状态在未审批的情况下)才能删除该工单 id: %s" %(id)
            wslog_error().error("用户: %s 删除 WorkFormModel 模型 id: %s 的对象失败,只有管理员或者(工单状态的发布者及工单状态在未审批的情况下)才能删除该工单" %(request.user.username,id))

        return JsonResponse(ret)

''' 工单中 SQL附件的上传 '''
class WorkFormUploadView(LoginRequiredMixin,View):
    allow_file_type=set(['txt','sql'])
    upload_dir = MEDIA_ROOT + 'pub/'
    max_file_size = 10 * 1024 * 1024

    def post(self,request):
        ret = {"result":0,"msg":None}
        files = request.FILES.getlist('files[]')
        for file in files:
            filename = file.name
            filesize = file.size
            if '.' not in filename or  filename.rsplit('.',1)[1] not in self.allow_file_type:
                ret["result"] = 1
                ret["msg"] = "The file '%s' format is not allow" %(filename)
                return JsonResponse(ret)
            if filesize >= self.max_file_size:
                ret["result"] = 1
                ret["msg"] = "The file '%s' size %s is more than 10Mb" %(filename,filesize)

            file_upload_time = datetime.now().strftime("%Y%m%d%H%M%S")
            file_store_name = filename.rsplit('.',1)[0] + '_' + file_upload_time + '.' + filename.rsplit('.',1)[1]
            file_url = reverse("workform_upload") + file_store_name
            store_dir_name = self.upload_dir + file_store_name
            try:
                with open(store_dir_name, 'wb+') as f:
                    for chunk in file.chunks():
                        f.write(chunk)
            except Exception as e:
                ret["result"] = 1
                ret["msg"] = "文件 %s 保存失败,错误信息: %s,请联系运维人员" %(filename,e.args)
            else:
                ret["files"] = [{"name": file_store_name}]
                ret["file_url"] = file_url

            return JsonResponse(ret)

''' 工单中 SQL 附件的预览'''
class WorkFormUploadFilePreviewView(LoginRequiredMixin,View):

    def download_file(self,filename):
        with open(filename,'rb') as f:
            c = f.read()
        return c.decode('utf-8').replace('\n','</br>')

    def get(self,request,**kwargs):
        filename = kwargs.get("filename")
        filename_path = MEDIA_ROOT + 'pub/' + filename

        if not os.path.exists(filename_path):
            return HttpResponse("该文件 %s 不存在或已被删除" %(filename_path))

        response=StreamingHttpResponse(self.download_file(filename_path))
        #response['Content-Type']="application/octet-stream" 
        #response['Content-Disposition']="attachment;filename='%s'" %(filename)
        return response   

