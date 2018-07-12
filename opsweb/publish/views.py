from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic import TemplateView,ListView,View
from dashboard.utils.wslog import wslog_error,wslog_info
from resources.models import CmdbModel,ServerModel
from publish.models import PublishVersionModel,PublishHistoryModel
from publish.forms import PublishPubForm
import subprocess
from ansi2html import Ansi2HTMLConverter
import sys
import os
import json
from datetime import *
from django.db.models import Q
from accounts.permission.permission_required_mixin import PermissionRequiredMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from publish.tasks import dingding_msg_send,wx_msg_send
from django.urls import reverse


history_dir = os.path.dirname(os.path.realpath(__file__)) + '/history/'
conv = Ansi2HTMLConverter()

class PublishPubView(LoginRequiredMixin,PermissionRequiredMixin,TemplateView):
    permission_required = "publish.add_publishhistorymodel"
    permission_redirect_url = "publish_list"

    template_name = "publish_pub.html"

    def get_context_data(self):
        context = super(PublishPubView,self).get_context_data()
        context["module_name_online"] = list(CmdbModel.objects.filter(env__exact='online',status__exact="0",dev_team__in=self.request.user.groups.all()).exclude(way='5').values("id","name").order_by("name"))
        context["module_name_gray"] = list(CmdbModel.objects.filter(env__exact='gray',status__exact="0",dev_team__in=self.request.user.groups.all()).exclude(way='5').values("id","name").order_by("name"))
        return context

class PublishAnsiblePlaybookView(LoginRequiredMixin,View):
    permission_required = ["publish.add_publishhistorymodel","publish.change_publishversionmodel"]

    def get(self,request):
        ret = {"result":0}
        shell_pid = request.GET.get("shell_pid")
        ph_id = request.GET.get("ph_id")
        ansible_log_file_pre = request.GET.get("ansible_log_file")
        ansible_log_file = history_dir + ansible_log_file_pre

        if not [ perm for perm in self.permission_required if request.user.has_perm(perm)]:
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有权限,请联系运维!"
            return JsonResponse(ret) 

        try:
            ph_obj = PublishHistoryModel.objects.get(id__exact=ph_id)
        except PublishHistoryModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "PublishHistoryModel 不存在 id: %s 的对象" %(ph_id)
            return JsonResponse(ret)

        with open(ansible_log_file,'r') as f1:
            lines_str = f1.read()
        process_filter = 'ps -p %s' %(shell_pid)
        shell_returncode = subprocess.call(process_filter,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        ret["shell_returncode"] = shell_returncode
        ret["ansible_log"] = conv.convert(lines_str)
        if shell_returncode != 0:
            if 'fatal' in lines_str or 'ERROR!' in lines_str:
                ph_obj.status = 'failure'
                pic_url = 'https://image.watsons.com.cn/failed_2.png'
                ret["errcode"] = 1
            else:
                ph_obj.status = 'success'
                pic_url = 'https://image.watsons.com.cn/success_2.png'
                ret["errcode"] = 0

            ph_obj.save(update_fields=["status"])
            try:
                dingding_title = "应用 %s: %s" %(ph_obj.get_type_display(),ph_obj.module_name.name)
                dingding_text = "发布 IP: %s \n发布版本: %s \n发布状态: %s\n发布人: %s \n打包人: %s \n发布时间: %s " %( \
                                                                                ' , '.join([i.get("private_ip") for i in ph_obj.ip.values("private_ip")]), \
                                                                                ph_obj.version_now.version,\
                                                                                ph_obj.status,\
                                                                                ph_obj.pub_user.userextend.cn_name,\
                                                                                ph_obj.version_now.pack_user,\
                                                                                ph_obj.pub_time.strftime("%Y-%m-%d %X")
                                                                                )

                dingding_messageUrl = "%s" %(request.get_host() + reverse("publish_list"))
                data = {"title":dingding_title,"text":dingding_text ,"messageUrl":dingding_messageUrl,"picUrl":pic_url}
                wx_data = {"title":dingding_title,"content":dingding_text.replace("\n","<br>"),"url":dingding_messageUrl}
                # dingding_msg_send.delay(data)
                # wx_msg_send.delay(wx_data)
            except:
                pass
        return JsonResponse(ret)

    def post(self,request):
        ret = {"result":0}
        pub_info_form = PublishPubForm(request.POST)

        ip_id_list = request.POST.getlist("ip")

        if not [ perm for perm in self.permission_required if request.user.has_perm(perm)]:
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有权限,请联系运维!"
            return JsonResponse(ret) 

        ip_obj_list = []
        for ip_id in ip_id_list:
            try:
                ip_obj = ServerModel.objects.get(id__exact=ip_id)
            except ServerModel.DoesNotExist:
                ret["result"] = 1
                ret["msg"] = "所选择的ip地址不存在,请刷新重试"
                return JsonResponse(ret)
            else:
                 ip_obj_list.append(ip_obj)

        if not pub_info_form.is_valid():
            ret["result"] = 1
            error_msg = json.loads(pub_info_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([ i["message"] for v in error_msg.values() for i in v ])
            return JsonResponse(ret)

        pub_info = pub_info_form.cleaned_data
        m_obj = pub_info.get("module_name")
        v_obj = pub_info.get("version")

        ''' 确定该用户是否有权限操作该模块的发布,是根据这个用户是否是这个模块管理组里的用户 '''
        if not m_obj.dev_team.filter(user__username__exact=request.user.username):
            ret["result"] = 1
            ret["msg"] = "你没有权限操作该应用: %s 的发布,因为你不在这个应用的管理组里，请联系运维..." %(m_obj.name)
            wslog_error().error(ret["msg"])
            return JsonResponse(ret) 

        if not m_obj.ansible_playbook:
            ret["result"] = 1
            ret["msg"] = "该应用: %s 未配置发布的 ansible playbook 脚本,请前往CMDB配置" %(m_obj.name)
            wslog_error().error(ret["msg"])
            return JsonResponse(ret)

        pub_shell = '/usr/bin/ansible-playbook %s -e "host=%s filename=%s"' %(m_obj.ansible_playbook,','.join([ ip.private_ip for ip in ip_obj_list ]),v_obj.version)
        history_file_name = pub_info.get("type") + '_' + m_obj.name + '_'  + "_".join([ ip.private_ip for ip in ip_obj_list ]).replace('.','-') + '_' + datetime.now().strftime("%Y%m%d%H%M%S") + '.txt'
        ansible_log_file = history_dir + history_file_name

        ph_obj = PublishHistoryModel()
        try:
            ph_obj.module_name = m_obj
            ph_obj.env = pub_info.get('env')
            ph_obj.type = pub_info.get('type')
            ph_obj.version_now = v_obj
            ph_obj.pub_user = request.user
            ph_obj.pub_log_file = history_file_name
            ph_obj.save()
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "添加 PublishHistoryModel 对象失败,请查看日志"
            wslog_error().error("添加 PublishHistoryModel 对象失败，错误日志: %s" %(e.args))
            return JsonResponse(ret)
        else:
            ph_obj.ip.set(ip_obj_list)

        try:
            with open(ansible_log_file,'a+') as f_history:
                f_history.write("\n")
                f_history.write("执行脚本: %s \n" %(m_obj.ansible_playbook))
                f_history.write("目标服务器: %s \n" %(','.join([ ip.private_ip for ip in ip_obj_list ])))
                f_history.write("发布版本号: %s \n" %(v_obj.version))
                f_history.write("\n")
                shell_subprocess = subprocess.Popen(pub_shell,shell=True,stdout=f_history,stderr=f_history)
                shell_pid = shell_subprocess.pid
        except:
            ret["result"] = 1
            ret["msg"] = "通过subprocess执行ansible playbook 失败"
            ph_obj.delete()
            return JsonResponse(ret)

        ''' 查询模块当前使用的主版本 '''
        try:
            module_version_run_obj = PublishVersionModel.objects.get(module_name__exact=m_obj,status__exact='running')
        except PublishVersionModel.MultipleObjectsReturned:
            ret["result"] = 1
            ret["msg"] = "查询模块: %s 当前使用的主版本不唯一,请修改 PublishVersionModel 中该模块的版本 running 状态为唯一值" %(m_obj.name)
            return JsonResponse(ret)
        except PublishVersionModel.DoesNotExist:
            module_version_run_obj = ''

        if not module_version_run_obj:
            v_obj.status = 'running'
            v_obj.save(update_fields=["status"])
        elif v_obj != module_version_run_obj:
            if ph_obj.type == 'publish':
                module_version_run_obj.status = 'run_pre'
            else:
                module_version_run_obj.status = 'rollback'
            module_version_run_obj.save(update_fields=["status"])
            v_obj.status = 'running'
            v_obj.save(update_fields=["status"])

        ret["msg"] = "正在执行playbook,稍后打印执行过程....."
        ret["ansible_log_file"] = history_file_name
        ret["shell_pid"] = shell_pid
        ret["ph_id"] = ph_obj.id

        return JsonResponse(ret)

class PublishListView(LoginRequiredMixin,ListView):
    template_name = "publish_history.html"
    model = PublishHistoryModel
    paginate_by = 10
    page_total = 11
    ordering = "-id"

    def get_context_data(self):
        context = super(PublishListView,self).get_context_data()
        context['page_range'] = self.get_page_range(context['page_obj'])
        search_data = self.request.GET.copy()
        try:
            search_data.pop('page')
        except:
            pass

        if search_data:
            context['search_uri'] = '&' + search_data.urlencode()
        else:
            context['search_uri'] = '' 
        context.update(search_data.dict())
        return context

    def get_queryset(self):
        queryset = super(PublishListView,self).get_queryset()

        search_name = self.request.GET.get('search',None)
        if search_name:
            queryset = queryset.filter(Q(module_name__name__icontains=search_name)|Q(ip__private_ip__icontains=search_name)|Q(version_now__version__icontains=search_name)).distinct()
        return queryset
    
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

class PublishInfoView(LoginRequiredMixin,ListView):
    def get(self,request):
        ret = {"result":0}
        ph_id = request.GET.get("id")
        try:
            ph_obj = PublishHistoryModel.objects.get(id__exact=ph_id)
        except PublishHistoryModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "PublishHistoryModel 查不到该记录 id: %s" %(ph_id)
            return JsonResponse(ret)
        else:
            history_file_name = ph_obj.pub_log_file    

        ansible_log_file = history_dir + history_file_name

        with open(ansible_log_file,'r') as f1:
            lines_str = f1.read()

        ret["msg"] = conv.convert(lines_str)
        
        return JsonResponse(ret)


class PublishDeleteView(LoginRequiredMixin,View):
    permission_required = "publish.delete_publishhistorymodel"

    def post(self,request):
        ret = {"result":0}
        ph_id = request.POST.get("id")

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有权限,请联系运维!"
            return JsonResponse(ret) 

        try:
            ph_obj = PublishHistoryModel.objects.get(id__exact=ph_id)
        except PublishHistoryModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "PublishHistoryModel 查不到该记录 id: %s" %(ph_id)
            return JsonResponse(ret)
        
        try:
            ph_obj.delete()
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "PublishHistoryModel 删除对象 id: %s 失败, 请查看日志" %(ph_id)
            wslog_error().error("PublishHistoryModel 删除对象 id: %s 失败, 错误信息: %s" %(ph_id,e.args))
        else:
            ret["msg"] = "PublishHistoryModel 删除对象 id: %s 成功" %(ph_id)

        return JsonResponse(ret)
