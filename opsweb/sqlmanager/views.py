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
from sqlmanager.models import DBModel,DBClusterModel,DBInstanceModel,ENV_CHOICES
from sqlmanager.forms import DBClusterAddForm,DBClusterChangeForm,DBAddForm,DBChangeForm,DBInstanceAddForm,DBInstanceChangeForm
from django.forms import model_to_dict
from django.contrib.auth.models import Group
from resources.models import ServerModel
from dashboard.utils.get_page_range import get_page_range

'''Mysql集群列表'''
class DBClusterListView(LoginRequiredMixin,ListView):
    template_name = "db_cluster_list.html"
    model = DBClusterModel
    paginate_by = 10
    ordering = '-id'
    page_total = 11

    def get_context_data(self, **kwargs):
        context = super(DBClusterListView, self).get_context_data(**kwargs)
        context['page_range'] = get_page_range(self.page_total,context['page_obj'])
        context["env_list"] = dict(ENV_CHOICES)
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
        queryset = super(DBClusterListView, self).get_queryset()
        search_name = self.request.GET.get('search', None)
        if search_name:
            queryset = queryset.filter(Q(name__icontains=search_name)|
                                       Q(w_vip__icontains=search_name)|
                                       Q(r_vip__icontains=search_name)|
                                       Q(w_domain_name__icontains=search_name)|
                                       Q(r_domain_name__icontains=search_name)
                                       )
        return queryset

'''添加Mysql集群'''
class DBClusterAddView(LoginRequiredMixin,View):
    permission_required = "sqlmanager.add_dbclustermodel"

    def post(self,request):
        ret = {"result":0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有权限,请联系运维!"
            return JsonResponse(ret)

        cluster_form = DBClusterAddForm(request.POST)
        if not cluster_form.is_valid():
            ret['result'] = 1
            error_msg = json.loads(cluster_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([i["message"] for v in error_msg.values() for i in v])
            return JsonResponse(ret)
        try:
            dbc = DBClusterModel(**cluster_form.cleaned_data)
            dbc.save()
            ret['msg'] = "Mysql 集群 %s 添加成功" % (cluster_form.cleaned_data.get('name'))
        except Exception as e:
            ret['result'] = 1
            ret['msg'] = "Mysql 集群 %s 添加失败，错误信息: %s" % (cluster_form.cleaned_data.get('name'),e.args)
            wslog_error().error("Mysql 集群 %s 添加失败，错误信息: %s" % (cluster_form.cleaned_data.get('name'),e.args))

        return JsonResponse(ret)

'''更新Mysql集群'''
class DBClusterChangeView(LoginRequiredMixin,View):
    permission_required = "sqlmanager.change_dbclustermodel"

    def get(self,request):
        ret = {'result': 0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有权限,请联系运维!"
            return JsonResponse(ret)

        dbc_id = request.GET.get('id', 0)
        print("dbc_id: ",dbc_id)
        try:
            dbc_obj = DBClusterModel.objects.get(id__exact=dbc_id)
            dbc_info = model_to_dict(dbc_obj)
        except Exception as e:
            ret['result'] = 1
            ret['msg'] = "获取 Msyql 集群: %s 信息失败,请查看日志..." %(dbc_id)
            wslog_error().error("获取 Msyql 集群: %s 信息失败,错误信息: %s" % (dbc_id,e.args))
        else:
            ret['dbc_info'] = dbc_info
        return JsonResponse(ret)

    def post(self,request):
        ret = {'result':0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有权限,请联系运维!"
            return JsonResponse(ret)

        cluster_change_form = DBClusterChangeForm(request.POST)
        if not cluster_change_form.is_valid():
            ret['result'] = 1
            error_msg = json.loads(cluster_change_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([i["message"] for v in error_msg.values() for i in v])
            return JsonResponse(ret)

        print("cluster_change_form.cleaned_data: ",cluster_change_form.cleaned_data)

        dbc_id = request.POST.get('id',0)
        try:
            dbc_obj = DBClusterModel.objects.get(id=dbc_id)
            dbc_obj.w_vip = cluster_change_form.cleaned_data.get("w_vip")
            dbc_obj.r_vip = cluster_change_form.cleaned_data.get("r_vip")
            dbc_obj.w_domain_name = cluster_change_form.cleaned_data.get("w_domain_name")
            dbc_obj.r_domain_name = cluster_change_form.cleaned_data.get("r_domain_name")
            dbc_obj.env = cluster_change_form.cleaned_data.get("env")
            dbc_obj.save(update_fields=["w_vip","r_vip","w_domain_name","r_domain_name","last_update_time","env"])
        except Exception as e:
            ret['result'] = 1
            ret['msg'] = "更新 Mysql 集群: %s 信息失败,请查看日志" %(dbc_id)
            wslog_error().error("更新 Mysql 集群: %s 信息失败,错误信息: %s" %(dbc_id,e.args))
        else:
            ret['msg'] = "更新 Mysql 集群: %s 信息成功" % (dbc_obj.name)
        return JsonResponse(ret)

'''删除Mysql集群'''
class DBClusterDeleteView(LoginRequiredMixin,View):
    permission_required = "sqlmanager.delete_dbclustermodel"

    def post(self,request):
        ret = {'result':0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有权限,请联系运维!"
            return JsonResponse(ret)

        dbc_id = request.POST.get('id',None)

        try:
            dbc_obj = DBClusterModel.objects.get(id=dbc_id)
            dbc_obj.delete()
        except DBClusterModel.DoesNotExist:
            ret['result'] = 1
            ret['msg'] = "删除 Msyql 集群失败,获取不到 Cluster id"
            wslog_error().error("删除 Mysql 集群: %s 失败,获取不到 Cluster id" % (dbc_id))
        except Exception as e:
            ret['result'] = 1
            ret['msg'] = "删除 Mysql 集群: %s 失败,请查看日志" %(dbc_id)
            wslog_error().error("删除 Mysql 集群: %s 失败,错误信息: %s" %(dbc_id,e.args))
        else:
            ret['msg'] = "Mysql 集群: %s 删除成功" % (dbc_obj.name)
        return JsonResponse(ret)

'''集群关联Mysql实例列表'''
class DBClusterRelateView(LoginRequiredMixin,TemplateView):
    template_name = "db_cluster_relate.html"

    def get_context_data(self, **kwargs):
        context = super(DBClusterRelateView, self).get_context_data(**kwargs)
        dbc_id = self.request.GET.get("id")
        dbc_obj = DBClusterModel.objects.get(id__exact=dbc_id)
        context["cluster_name"] = dbc_obj.name
        context["cluster_relate_instance_list"] = dbc_obj.dbinstancemodel_set.all()
        context["cluster_relate_dbs_list"] = dbc_obj.dbmodel_set.all()
        return context

'''Mysql库列表'''
class DBListView(LoginRequiredMixin,ListView):
    template_name = "db_list.html"
    model = DBModel
    paginate_by = 10
    ordering = '-id'
    page_total = 11

    def get_context_data(self, **kwargs):
        context = super(DBListView, self).get_context_data(**kwargs)
        context["group_list"] = Group.objects.values("id","name")
        context["cluster_list"] = DBClusterModel.objects.values("id","name")
        context['page_range'] = get_page_range(self.page_total,context['page_obj'])
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
        queryset = super(DBListView, self).get_queryset()
        search_name = self.request.GET.get('search', None)
        if search_name:
            queryset = queryset.filter(name__icontains=search_name)
        return queryset

'''添加Mysql库'''
class DBAddView(LoginRequiredMixin,View):
    permission_required = "sqlmanager.add_dbmodel"
    def post(self,request):
        ret = {"result":0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有权限,请联系运维!"
            return JsonResponse(ret)

        db_form = DBAddForm(request.POST)
        if not db_form.is_valid():
            ret['result'] = 1
            error_msg = json.loads(db_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([i["message"] for v in error_msg.values() for i in v])
            return JsonResponse(ret)

        manager_group_obj_list = db_form.cleaned_data.get("db_manage_group")
        cluster_obj_list = db_form.cleaned_data.get("cluster_name")
        del db_form.cleaned_data["db_manage_group"]
        del db_form.cleaned_data["cluster_name"]

        try:
            db_obj = DBModel(**db_form.cleaned_data)
            db_obj.save()
            db_obj.db_manage_group.set(manager_group_obj_list)
            db_obj.cluster_name.set(cluster_obj_list)
        except Exception as e:
            ret['result'] = 1
            ret['msg'] = "Mysql %s 添加失败,错误信息: %s" % (db_form.cleaned_data.get('name'),e.args)
            wslog_error().error("Mysql %s 添加失败,错误信息: %s" % (db_form.cleaned_data.get('name'),e.args))
        else:
            ret['msg'] = "Mysql %s 添加成功" % (db_form.cleaned_data.get('name'))

        return JsonResponse(ret)

'''更新Mysql库'''
class DBChangeView(View):
    permission_required = "sqlmanager.change_dbmodel"

    def get(self,request):
        ret = {"result":0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有权限,请联系运维!"
            return JsonResponse(ret)

        db_id = request.GET.get("id")
        try:
            db_obj = DBModel.objects.get(id__exact=db_id)
        except DBModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "DBModel 中不存在 id: %s 的对象，请刷新重试..." %(db_id)
        else:
            db_info = model_to_dict(db_obj)
            db_info["db_manage_group"] = [g.id for g in db_info["db_manage_group"]]
            db_info["cluster_name"] = [c.id for c in db_info["cluster_name"]]
            ret["db_info"] = db_info

        return JsonResponse(ret)

    def post(self,request):
        ret = {"result":0}
        db_id = request.POST.get("id")

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有权限,请联系运维!"
            return JsonResponse(ret)

        db_change_form = DBChangeForm(request.POST)
        if not db_change_form.is_valid():
            ret['result'] = 1
            error_msg = json.loads(db_change_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([i["message"] for v in error_msg.values() for i in v])
            return JsonResponse(ret)

        try:
            db_obj = DBModel.objects.get(id__exact=db_id)
            db_obj.save(update_fields=["last_update_time"])
            db_obj.manage_group.set(db_change_form.cleaned_data.get("manage_group"))
            db_obj.cluster.set(db_change_form.cleaned_data.get("cluster"))
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "DBModel 更新 id: %s 的对象失败，错误信息: %s" % (db_id,e.args)
            wslog_error().error("DBModel 更新 id: %s 的对象失败，错误信息: %s" % (db_id,e.args))
        else:
            ret["msg"] = "DBModel 更新 id: %s 的对象成功" % (db_id)

        return JsonResponse(ret)

'''删除Mysql库'''
class DBDeleteView(LoginRequiredMixin,View):
    permission_required = "sqlmanager.delete_dbmodel"

    def post(self,request):
        ret = {'result':0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有权限,请联系运维!"
            return JsonResponse(ret)

        db_id = request.POST.get('id',None)

        try:
            db_obj = DBModel.objects.get(id=db_id)
            db_obj.delete()
        except DBModel.DoesNotExist:
            ret['result'] = 1
            ret['msg'] = "删除 Msyql 库失败,获取不到 Cluster id"
            wslog_error().error("删除 Mysql 库: %s 失败,获取不到 Cluster id" % (db_id))
        except Exception as e:
            ret['result'] = 1
            ret['msg'] = "删除 Mysql 库: %s 失败,请查看日志" %(db_id)
            wslog_error().error("删除 Mysql 库: %s 失败,错误信息: %s" %(db_id,e.args))
        else:
            ret['msg'] = "Mysql 库: %s 删除成功" % (db_obj.name)

        return JsonResponse(ret)

'''Mysql实例列表'''
class DBInstanceListView(LoginRequiredMixin,ListView):
    template_name = "db_instance_list.html"
    model = DBInstanceModel
    paginate_by = 10
    ordering = '-id'
    page_total = 11

    def get_context_data(self, **kwargs):
        context = super(DBInstanceListView, self).get_context_data(**kwargs)
        context["cluster_online_list"] = list(DBClusterModel.objects.filter(env__exact="online").values("id", "name"))
        context["cluster_gray_list"] = list(DBClusterModel.objects.filter(env__exact="gray").values("id", "name"))
        context["role_list"] = dict(DBInstanceModel.ROLE_CHOICES)
        context["backup_list"] = dict(DBInstanceModel.BACKUP_CHOICES)
        context["server_list"] = list(ServerModel.objects.values("id","private_ip"))
        context["env_list"] = dict(ENV_CHOICES)
        context['page_range'] = get_page_range(self.page_total,context['page_obj'])
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
        queryset = super(DBInstanceListView, self).get_queryset()
        search_name = self.request.GET.get('search', None)
        if search_name:
            queryset = queryset.filter(Q(name__icontains=search_name)|Q(ins_ip__private_ip__icontains=search_name))
        return queryset

'''添加Mysql实例'''
class DBInstanceAddView(LoginRequiredMixin,View):
    permission_required = "sqlmanager.add_dbinstancemodel"

    def post(self,request):
        ret = {"result":0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有权限,请联系运维!"
            return JsonResponse(ret)

        dbi_form = DBInstanceAddForm(request.POST)
        if not dbi_form.is_valid():
            ret['result'] = 1
            error_msg = json.loads(dbi_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([i["message"] for v in error_msg.values() for i in v])
            return JsonResponse(ret)
        print("dbi_form.cleaned_data: ",dbi_form.cleaned_data)
        try:
            dbi_obj = DBInstanceModel(**dbi_form.cleaned_data)
            dbi_obj.save()
        except Exception as e:
            ret['result'] = 1
            ret['msg'] = "Mysql 实例 %s 添加失败,错误信息: %s" % (dbi_form.cleaned_data.get('name'),e.args)
            wslog_error().error("Mysql 实例 %s 添加失败,错误信息: %s" % (dbi_form.cleaned_data.get('name'),e.args))
        else:
            ret['msg'] = "Mysql 实例 %s 添加成功" % (dbi_form.cleaned_data.get('name'))

        return JsonResponse(ret)

'''更多Mysql实例信息'''
class DBInstanceMoreInfoView(View):
    def get(self,request):
        ret = {"result":0}
        dbi_id = request.GET.get("id")
        try:
            dbi_obj = DBInstanceModel.objects.get(id__exact=dbi_id)
        except DBInstanceModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "DBInstanceModel 不存在id: %s 的对象，请刷新重试..." %(dbi_id)
            return JsonResponse(ret)
        try:
            dbi_more_info = model_to_dict(dbi_obj,fields=["name","scripts","data_dir","backup_dir"])
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "DBInstanceModel id: %s 的对象转 dict 失败，错误信息: %s" % (dbi_id,e.args)
            wslog_error().error("DBInstanceModel id: %s 的对象转 dict 失败，错误信息: %s" % (dbi_id,e.args))
        else:
            ret["dbi_more_info"] = dbi_more_info

        return JsonResponse(ret)

'''更新Mysql实例'''
class DBInstanceChangeView(View):
    permission_required = "sqlmanager.change_dbinstancemodel"

    def get(self,request):
        ret = {"result":0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有权限,请联系运维!"
            return JsonResponse(ret)

        dbi_id = request.GET.get("id")
        try:
            dbi_obj = DBInstanceModel.objects.get(id__exact=dbi_id)
        except DBInstanceModel.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "DBInstanceModel 中不存在 id: %s 的对象，请刷新重试..." %(dbi_id)
        else:
            dbi_info = model_to_dict(dbi_obj)
            ret["dbi_info"] = dbi_info

        return JsonResponse(ret)

    def post(self,request):
        ret = {"result":0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有权限,请联系运维!"
            return JsonResponse(ret)

        dbi_id = request.POST.get("id")

        dbi_change_form = DBInstanceChangeForm(request.POST)
        if not dbi_change_form.is_valid():
            ret['result'] = 1
            error_msg = json.loads(dbi_change_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([i["message"] for v in error_msg.values() for i in v])
            return JsonResponse(ret)

        try:
            dbi_obj = DBInstanceModel.objects.get(id__exact=dbi_id)
            dbi_obj.ins_cluster = dbi_change_form.cleaned_data.get("ins_cluster")
            dbi_obj.ins_ip = dbi_change_form.cleaned_data.get("ins_ip")
            dbi_obj.role = dbi_change_form.cleaned_data.get("role")
            dbi_obj.backup = dbi_change_form.cleaned_data.get("backup")
            dbi_obj.env = dbi_change_form.cleaned_data.get("env")
            dbi_obj.port = dbi_change_form.cleaned_data.get("port")
            dbi_obj.data_dir = dbi_change_form.cleaned_data.get("data_dir")
            dbi_obj.backup_dir = dbi_change_form.cleaned_data.get("backup_dir")
            dbi_obj.scripts = dbi_change_form.cleaned_data.get("scripts")
            dbi_obj.save(update_fields=["ins_cluster","last_update_time","ins_ip","role","backup","env","backup_dir","data_dir","scripts","port"])
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "DBInstanceModel 更新 id: %s 的对象失败，错误信息: %s" % (dbi_id,e.args)
            wslog_error().error("DBInstanceModel 更新 id: %s 的对象失败，错误信息: %s" % (dbi_id,e.args))
        else:
            ret["msg"] = "DBInstanceModel 更新 id: %s 的对象成功" % (dbi_id)

        return JsonResponse(ret)

'''删除Mysql实例'''
class DBInstanceDeleteView(LoginRequiredMixin,View):
    permission_required = "sqlmanager.delete_dbinstancemodel"

    def post(self,request):
        ret = {'result':0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有权限,请联系运维!"
            return JsonResponse(ret)

        dbi_id = request.POST.get('id',None)

        try:
            dbi_obj = DBInstanceModel.objects.get(id=dbi_id)
            dbi_obj.delete()
        except DBInstanceModel.DoesNotExist:
            ret['result'] = 1
            ret['msg'] = "删除 Msyql 实例失败,获取不到 id"
            wslog_error().error("删除 Mysql 实例: %s 失败,获取不到 Cluster id" % (dbi_id))
        except Exception as e:
            ret['result'] = 1
            ret['msg'] = "删除 Mysql 实例: %s 失败,请查看日志" %(db_id)
            wslog_error().error("删除 Mysql 实例: %s 失败,错误信息: %s" %(dbi_id,e.args))
        else:
            ret['msg'] = "Mysql 实例: %s 删除成功" % (dbi_obj.name)

        return JsonResponse(ret)

