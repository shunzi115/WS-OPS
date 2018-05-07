from django.http import HttpResponse, JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, TemplateView, View
from resources.models import FirewallRulesModel
from django.shortcuts import reverse, redirect
from accounts.permission.permission_required_mixin import PermissionRequiredMixin
from resources.forms import FirewallRulesForm,FirewallRulesChangeForm
import json
from django.forms.models import model_to_dict
from dashboard.utils.wslog import wslog_error, wslog_info
from django.db.models import Q
from django.core import serializers


class FirewallRulesListView(LoginRequiredMixin, ListView):
    template_name = "firewall_rules/firewall_rules_list.html"
    model = FirewallRulesModel
    paginate_by = 10
    ordering = "id"
    page_total = 11

    def get_context_data(self, **kwargs):
        context = super(FirewallRulesListView, self).get_context_data(**kwargs)
        context['page_range'] = self.get_page_range(context['page_obj'])
        json_data = serializers.serialize("json", self.get_queryset(), fields=("s_hostname", "s_ip", "d_hostname", \
                                                                               "d_ip", "d_port", "protocol", \
                                                                               "app_name", "applicant", \
                                                                               "create_time", "expiry_date", \
                                                                               "commit_by", "action", \
                                                                               "comment"))
        json_data_pre_list = [i["fields"] for i in json.loads(json_data)]
        context["firewall_rules_json_data"] = json.dumps(json_data_pre_list)
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

    # 过滤模型中的数据
    def get_queryset(self):
        queryset = super(FirewallRulesListView, self).get_queryset()
        search_name = self.request.GET.get('search', '')
        if search_name:
            queryset = queryset.filter(Q(s_ip__icontains=search_name)
                                       | Q(d_ip__icontains=search_name)
                                       | Q(commit_by__icontains=search_name)
                                       | Q(comment__icontains=search_name)).distinct()
        return queryset

    # 获取要展示的页数范围,这里是固定显示多少页
    def get_page_range(self, page_obj):
        page_now = page_obj.number
        if page_obj.paginator.num_pages > self.page_total:
            page_start = page_now - self.page_total // 2
            page_end = page_now + self.page_total // 2 + 1

            if page_start <= 0:
                page_start = 1
                page_end = page_start + self.page_total
            if page_end > page_obj.paginator.num_pages:
                page_end = page_obj.paginator.num_pages + 1
                page_start = page_end - self.page_total
        else:
            page_start = 1
            page_end = page_obj.paginator.num_pages + 1

        page_range = range(page_start, page_end)
        return page_range

class FirewallRulesImportView(LoginRequiredMixin,TemplateView):
    template_name = 'firewall_rules/firewall_rules_import.html'

    def post(self,request):
        ret = {"result":0}
        user_obj = request.user

        firewall_rules_pre = request.POST.get("firewall_rules",None)
        if not firewall_rules_pre :
            ret["result"] = 1
            ret["msg"] = "防火墙工单必须导入包含防火墙策略的xlsx表"
            return JsonResponse(ret)

        firewall_rules_list = json.loads(firewall_rules_pre)

        for fr in firewall_rules_list:
            firewall_rule_form = FirewallRulesForm(fr)
            if not firewall_rule_form.is_valid():
                ret["result"] = 1
                error_msg = json.loads(firewall_rule_form.errors.as_json(escape_html=False))
                fr_error = "%s -> %s:%s" %(fr.get("s_ip",None),fr.get("d_ip",None),fr.get("d_port",None))
                ret["msg"] = '\n'.join([i["message"] for v in error_msg.values() for i in v]) + '\n' + fr_error
                return JsonResponse(ret)
            try:
                fr_obj = FirewallRulesModel(**firewall_rule_form.cleaned_data)
                fr_obj.commit_by = user_obj.username
                fr_obj.save()
            except Exception as e:
                ret["result"] = 1
                ret["msg"] = "FirewallRulesModel 模型对象保存失败,错误信息: %s" % (e.args)
                wslog_error().error("添加 FirewallRulesModel 模型对象 '%s -> %s:%s' 失败,错误信息: %s" % (firewall_rule_form.cleaned_data.get('s_ip') ,\
                                                                                                       firewall_rule_form.cleaned_data.get('d_ip'),\
                                                                                                       firewall_rule_form.cleaned_data.get('d_port'),\
                                                                                                       e.args))
                return JsonResponse(ret)

        ret["msg"] = "防火墙规则导入成功"
        wslog_info().info("防火墙规则导入成功")

        return JsonResponse(ret)

class FirewallRulesExportView(LoginRequiredMixin,View):
    def post(self,request):
        ret = {"result":0}
        search_name = request.POST.get("search_data",'')
        try:
            firewall_rules_list = FirewallRulesModel.objects.filter(Q(s_ip__icontains=search_name)
                                                                    | Q(d_ip__icontains=search_name)
                                                                    | Q(commit_by__icontains=search_name)
                                                                    | Q(comment__icontains=search_name)).distinct()
            json_data = serializers.serialize("json", firewall_rules_list, fields=("s_hostname", "s_ip", "d_hostname", \
                                                                                    "d_ip", "d_port", "protocol", \
                                                                                    "app_name", "applicant", \
                                                                                    "create_time", "expiry_date", \
                                                                                    "commit_by", "action", \
                                                                                    "comment"))
            json_data_pre_list = [i["fields"] for i in json.loads(json_data)]
            ret["firewall_rules_json_data"] = json.dumps(json_data_pre_list)
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "FirewallRulesModel 模型对象序列化为json失败，请查看日志..."
            wslog_error().error("FirewallRulesModel 模型对象序列化为json失败，错误信息: %s" %(e.args))

        return JsonResponse(ret)

class FirewallRulesChangeView(LoginRequiredMixin,View):
    permission_required = "resources.change_firewallrulesmodel"

    def get(self, request):
        ret = {"result": 0}
        fr_id = request.GET.get("id", 0)

        ## ajax 请求的权限验证
        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有权限,请联系运维!"
            return JsonResponse(ret)

        try:
            fr_obj = FirewallRulesModel.objects.get(id__exact=fr_id)
        except FirewallRulesModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "FirewallRulesModel id: %s 不存在,请刷新重试" % (fr_id)
            wslog_error().error("FirewallRulesModel 模型对象id: %s 不存在" % (fr_id))
            return JsonResponse(ret)
        try:
            fr_info = model_to_dict(fr_obj)
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "FirewallRulesModel 模型对象转dict 失败,请查看日志"
            wslog_error().error("FirewallRulesModel 模型对象id: %s 转dict 失败,错误信息: %s" % (fr_id, e.args))
        else:
            ret["fr_info"] = fr_info
            wslog_info().info("FirewallRulesModel 模型对象id: %s 查询成功并返回给前端" % (fr_id))

        return JsonResponse(ret)

    def post(self, request):
        ret = {"result": 0}

        ## ajax 请求的权限验证
        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有权限,请联系运维!"
            return JsonResponse(ret)

        fr_id = request.POST.get("id", 0)
        fr_form = FirewallRulesChangeForm(request.POST)

        if not fr_form.is_valid():
            ret['result'] = 1
            error_msg = json.loads(fr_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([i["message"] for v in error_msg.values() for i in v])
            return JsonResponse(ret)

        try:
            fr_obj = FirewallRulesModel.objects.get(id__exact=fr_id)
        except FirewallRulesModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "FirewallRulesModel id: %s 不存在,请刷新重试" % (fr_id)
            wslog_error().error("FirewallRulesModel 模型对象id: %s 不存在" % (fr_id))
            return JsonResponse(ret)

        fr_change_info = fr_form.cleaned_data
        try:
            fr_obj.s_hostname = fr_change_info.get("s_hostname")
            fr_obj.s_ip = fr_change_info.get("s_ip")
            fr_obj.d_hostname = fr_change_info.get("d_hostname")
            fr_obj.d_ip = fr_change_info.get("d_ip")
            fr_obj.d_port = fr_change_info.get("d_port")
            fr_obj.protocol = fr_change_info.get("protocol")
            fr_obj.comment = fr_change_info.get("comment")
            fr_obj.update_user = request.user.username
            fr_obj.save(update_fields=["s_hostname", "s_ip", "d_hostname", "d_ip","d_port", "protocol","comment", "update_user","last_update_time"])
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "FirewallRulesModel: %s 修改规则保存失败,请查看日志" % (fr_id)
            wslog_error().error("FirewallRulesModel: id-%s 保存修改规则失败,错误信息: %s" % (fr_id, e.args))
        else:
            ret["msg"] = "FirewallRulesModel: %s 更改规则成功" % (fr_id)
            wslog_info().info("FirewallRulesModel: id-%s 更改规则成功" % (fr_id))

        return JsonResponse(ret)

class FirewallRulesDeleteView(LoginRequiredMixin,View):
    permission_required = "resources.delete_firewallrulesmodel"

    def post(self,request):
        ret = {'result':0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有权限,请联系运维!"
            return JsonResponse(ret)

        fr_id = request.POST.get('id',None)

        try:
            fr_obj = FirewallRulesModel.objects.get(id=fr_id)
            fr_obj.delete()
            ret['msg'] = "%s-->%s:%s 防火墙规则删除成功" %(fr_obj.s_ip,fr_obj.d_ip,fr_obj.d_port)
        except FirewallRulesModel.DoesNotExist:
            ret['result'] = 1
            ret['msg'] = "防火墙规则删除失败,获取不到 id"
            return JsonResponse(ret)
        return JsonResponse(ret)