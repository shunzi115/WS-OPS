from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic import TemplateView,ListView,View
from dashboard.utils.wslog import wslog_error,wslog_info
from resources.models import CmdbModel,ServerModel
import sys
import os
import json
from datetime import *
from django.db.models import Q
from accounts.permission.permission_required_mixin import PermissionRequiredMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from djcelery.models import CrontabSchedule,IntervalSchedule,PeriodicTask,TaskMeta,TaskState
from taskschedule.forms import CrontabScheduleForm,IntervalScheduleForm,TaskAddForm,TaskUpdateForm
from django.forms.models import model_to_dict
from celery.task.control import inspect
from itertools import chain

class TimeScheduleListView(LoginRequiredMixin,TemplateView):
    template_name = "time_schedule_list.html"

    def get_context_data(self):
        context = super(TimeScheduleListView,self).get_context_data()
        context["crontab_list"] = CrontabSchedule.objects.all()
        context["interval_list"] = IntervalSchedule.objects.all()
        return context

class CrontabScheduleAddView(LoginRequiredMixin,View):
    permission_required = "djcelery.add_crontabschedule"

    def post(self,request):
        ret = {"result":0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有'添加 CrontabSchedule '的权限,请联系运维!"
            return JsonResponse(ret)        

        crontab_schedule_add_form = CrontabScheduleForm(request.POST)
        if not crontab_schedule_add_form.is_valid():
            ret["result"] = 1
            error_msg = json.loads(crontab_schedule_add_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([i["message"] for v in error_msg.values() for i in v])
            return JsonResponse(ret)

        try:
            cs_obj =  CrontabSchedule(**crontab_schedule_add_form.cleaned_data)
            cs_obj.save()
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "CrontabSchedule 保存对象失败，请查看日志..."
            wslog_error().error("CrontabSchedule 保存对象失败, 错误信息: %s" %(e.args))
        else:
            ret["msg"] = "添加 CrontabSchedule 对象成功"
        return JsonResponse(ret)

class IntervalScheduleAddView(LoginRequiredMixin,View):
    permission_required = "djcelery.add_intervalschedule"

    def post(self,request):
        ret = {"result":0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有'添加 IntervalSchedule '的权限,请联系运维!"
            return JsonResponse(ret)

        interval_schedule_add_form = IntervalScheduleForm(request.POST)
        if not interval_schedule_add_form.is_valid():
            ret["result"] = 1
            error_msg = json.loads(interval_schedule_add_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([i["message"] for v in error_msg.values() for i in v])
            return JsonResponse(ret)

        try:
            cs_obj =  IntervalSchedule(**interval_schedule_add_form.cleaned_data)
            cs_obj.save()
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "IntervalSchedule 保存对象失败，请查看日志..."
            wslog_error().error("IntervalSchedule 保存对象失败, 错误信息: %s" %(e.args))
        else:
            ret["msg"] = "添加 IntervalSchedule 对象成功"
        return JsonResponse(ret)

class CrontabScheduleUpdateView(LoginRequiredMixin,View):
    permission_required = "djcelery.change_crontabschedule"
   
    def get(self,request):
        ret = {"result": 0}
        cs_id = request.GET.get("id")
        try:
            cs_obj = CrontabSchedule.objects.get(id__exact=cs_id)
        except CrontabSchedule.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "CrontabSchedule 模型中不存在 id: %s 的对象, 请刷新重试..." %(cs_id)
            returnJsonResponse(ret)
        ret["cs_info"] = model_to_dict(cs_obj)
        return JsonResponse(ret)

    def post(self,request):
        ret = {"result":0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有'修改 CrontabSchedule '的权限,请联系运维!"
            return JsonResponse(ret)

        cs_id = request.POST.get("id")
        try:
            cs_obj = CrontabSchedule.objects.get(id__exact=cs_id)
        except CrontabSchedule.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "CrontabSchedule 模型中不存在 id: %s 的对象, 请刷新重试..." % (cs_id)
            returnJsonResponse(ret)

        crontab_schedule_update_form = CrontabScheduleForm(request.POST)
        if not crontab_schedule_update_form.is_valid():
            ret["result"] = 1
            error_msg = json.loads(crontab_schedule_update_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([i["message"] for v in error_msg.values() for i in v])
            return JsonResponse(ret)
        cs_update_data = crontab_schedule_update_form.cleaned_data
        try:
            cs_obj.minute = cs_update_data.get("minute")
            cs_obj.hour = cs_update_data.get("hour")
            cs_obj.day_of_week = cs_update_data.get("day_of_week")
            cs_obj.day_of_month = cs_update_data.get("day_of_month")
            cs_obj.month_of_year = cs_update_data.get("month_of_year")
            cs_obj.save(update_fields=["minute","hour","day_of_week","day_of_month","month_of_year"])
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "CrontabSchedule 保存对象失败，请查看日志..."
            wslog_error().error("CrontabSchedule 保存对象失败, 错误信息: %s" %(e.args))
        else:
            ret["msg"] = "更新 CrontabSchedule 对象成功"
        return JsonResponse(ret)

class IntervalScheduleUpdateView(LoginRequiredMixin,View):
    permission_required = "djcelery.change_intervalschedule"

    def get(self,request):
        ret = {"result": 0}
        is_id = request.GET.get("id")
        try:
            is_obj = IntervalSchedule.objects.get(id__exact=is_id)
        except IntervalSchedule.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "IntervalSchedule 模型中不存在 id: %s 的对象, 请刷新重试..." %(is_id)
            return JsonResponse(ret)
        ret["is_info"] = model_to_dict(is_obj)
        return JsonResponse(ret)

    def post(self,request):
        ret = {"result":0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有'修改 IntervalSchedule '的权限,请联系运维!"
            return JsonResponse(ret)

        is_id = request.POST.get("id")
        try:
            is_obj = IntervalSchedule.objects.get(id__exact=int(is_id))
        except IntervalSchedule.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "IntervalSchedule 模型中不存在 id: %s 的对象, 请刷新重试..." % (is_id)
            return JsonResponse(ret)

        interval_schedule_update_form = IntervalScheduleForm(request.POST)
        if not interval_schedule_update_form.is_valid():
            ret["result"] = 1
            error_msg = json.loads(interval_schedule_update_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([i["message"] for v in error_msg.values() for i in v])
            return JsonResponse(ret)
        is_update_data = interval_schedule_update_form.cleaned_data
        try:
            is_obj.every = is_update_data.get("every")
            is_obj.period = is_update_data.get("period")
            is_obj.save(update_fields=["every","period"])
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "IntervalSchedule 保存对象失败，请查看日志..."
            wslog_error().error("IntervalSchedule 保存对象 id: %s 失败, 错误信息: %s" %(is_id,e.args))
        else:
            ret["msg"] = "更新IntervalSchedule 对象成功"
        return JsonResponse(ret)

class CrontabScheduleDeleteView(LoginRequiredMixin,View):
    permission_required = "djcelery.delete_crontabschedule"

    def post(self,request):
        ret = {"result":0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有'删除 CrontabSchedule '的权限,请联系运维!"
            return JsonResponse(ret)

        cs_id = request.POST.get("id")
        try:
            cs_obj = CrontabSchedule.objects.get(id__exact=cs_id)
            cs_obj.delete()
        except CrontabSchedule.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "CrontabSchedule 模型不存在 id: %s 的对象,请刷新重试" % (cs_id)
            return JsonResponse(ret)
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "CrontabSchedule 模型删除 id: %s 的对象失败,请查看日志" % (cs_id)
            wslog_error().error("CrontabSchedule 模型删除 id %s 的对象失败,错误信息: %s" % (cs_id, e.args))
            return JsonResponse(ret)
        else:
            ret["msg"] = "CrontabSchedule 模型删除 id: %s 的对象成功" % (cs_id)

        return JsonResponse(ret)

class IntervalScheduleDeleteView(LoginRequiredMixin,View):
    permission_required = "djcelery.delete_intervalschedule"

    def post(self,request):
        ret = {"result":0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有'删除 IntervalSchedule '的权限,请联系运维!"
            return JsonResponse(ret)    

        is_id = request.POST.get("id")
        try:
            is_obj = IntervalSchedule.objects.get(id__exact=is_id)
            is_obj.delete()
        except IntervalSchedule.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "IntervalSchedule 模型不存在 id: %s 的对象,请刷新重试" % (is_id)
            return JsonResponse(ret)
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "IntervalSchedule 模型删除 id: %s 的对象失败,请查看日志" % (is_id)
            wslog_error().error("IntervalSchedule 模型删除 id %s 的对象失败,错误信息: %s" % (is_id, e.args))
            return JsonResponse(ret)
        else:
            ret["msg"] = "IntervalSchedule 模型删除 id: %s 的对象成功" % (is_id)

        return JsonResponse(ret)

class TaskListView(LoginRequiredMixin,ListView):
    model = PeriodicTask
    template_name = "task_list.html"
    paginate_by = 10
    page_total = 11
    ordering = "-id"

    def get_context_data(self, **kwargs):
        context = super(TaskListView, self).get_context_data(**kwargs)
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
        queryset = super(TaskListView, self).get_queryset()
        queryset = queryset.exclude(task__exact='celery.backend_cleanup')
        search_name = self.request.GET.get('search', None)
        if search_name:
            queryset = queryset.filter(Q(name__icontains=search_name) | Q(task__icontains=search_name)).distinct()
        return queryset

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

class TaskAddView(LoginRequiredMixin,PermissionRequiredMixin,TemplateView):
    permission_required = "djcelery.add_periodictask"
    permission_redirect_url = "task_list"

    template_name = 'task_add.html'
    i_obj = inspect()
    def get_context_data(self, **kwargs):
        context = super(TaskAddView,self).get_context_data(**kwargs)
        context["crontab_schedule_list"] = list(CrontabSchedule.objects.values())
        context["interval_schedule_list"] = list(IntervalSchedule.objects.values())
        context["registered_tasks_list"] = list(set(chain.from_iterable(self.i_obj.registered_tasks().values())))
        return context

    def post(self,request):
        ret = {"result":0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有'添加定时任务'的权限,请联系运维!"
            return JsonResponse(ret)

        task_add_form = TaskAddForm(request.POST)
        if not task_add_form.is_valid():
            ret["result"] = 1
            error_msg = json.loads(task_add_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([i["message"] for v in error_msg.values() for i in v])
            return JsonResponse(ret)
        else:
            del task_add_form.cleaned_data["schedule"]

        print("task_add_form.cleaned_data: ",task_add_form.cleaned_data)

        if request.POST.get("expires"):
            task_add_form.cleaned_data["expires"] = datetime.strptime(request.POST.get("expires"),'%Y/%m/%d %H:%M')
        try:
            pt_obj =  PeriodicTask(**task_add_form.cleaned_data)
            pt_obj.save()
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "PeriodicTask 保存对象失败，请查看日志..."
            wslog_error().error("PeriodicTask 保存对象失败, 错误信息: %s" %(e.args))
        else:
            ret["msg"] = "添加 PeriodicTask 对象成功"

        return JsonResponse(ret)

class TaskInfoView(LoginRequiredMixin,View):
    def get(self,request):
        ret = {"result": 0}
        pt_id = request.GET.get("id")
        try:
            pt_obj = PeriodicTask.objects.get(id__exact=pt_id)
        except PeriodicTask.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "PeriodicTask 模型中不存在ID: %s 的对象,请刷新重试..." %(pt_id)
            return JsonResponse(ret)

        try:
            pt_info = model_to_dict(pt_obj)
            pt_info["enabled"] = '0' if pt_obj.enabled else '1'
            pt_info["schedule"] = "%s %s %s %s %s" %(pt_obj.crontab.minute,\
                                                        pt_obj.crontab.hour,\
                                                        pt_obj.crontab.day_of_month,\
                                                        pt_obj.crontab.month_of_year,\
                                                        pt_obj.crontab.day_of_week) \
                                                        if pt_obj.crontab else "%s %s" %(pt_obj.interval.every,pt_obj.interval.period)
            pt_info["date_changed"] = pt_obj.date_changed.strftime("%Y-%m-%d %X") if pt_obj.date_changed else ''
            pt_info["expires"] = pt_obj.expires.strftime("%Y-%m-%d %X") if pt_obj.expires else ''
            pt_info["last_run_at"] = pt_obj.last_run_at.strftime("%Y-%m-%d %X") if pt_obj.last_run_at else ''
            pt_info["total_run_count"] = pt_obj.total_run_count
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "对象 %s 转dict失败，请查看日志..." %(pt_obj.name)
            wslog_error().error("对象 %s 转dict失败,错误信息: %s" %(pt_obj.name,e.args))
        else:
            ret["pt_info"] = pt_info

        return JsonResponse(ret)

class TaskUpdateView(LoginRequiredMixin,View):
    permission_required = "djcelery.change_periodictask"

    def get(self,request):
        ret = {"result": 0}
        pt_id = request.GET.get("id")
        try:
            pt_obj = PeriodicTask.objects.get(id__exact=pt_id)
        except PeriodicTask.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "PeriodicTask 模型中不存在ID: %s 的对象,请刷新重试..." %(pt_id)
            return JsonResponse(ret)

        try:
            pt_info = model_to_dict(pt_obj)
            pt_info["schedule"] = 'crontab' if pt_obj.crontab else "interval"
            pt_info["expires"] = pt_obj.expires.strftime("%Y/%m/%d %H:%M") if pt_obj.expires else ''
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "对象 %s 转dict失败，请查看日志..." %(pt_obj.name)
            wslog_error().error("对象 %s 转dict失败,错误信息: %s" %(pt_obj.name,e.args))
        else:
            ret["pt_info"] = pt_info

        return JsonResponse(ret)

    def post(self,request):
        ret = {"result":0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有'修改定时任务'的权限,请联系运维!"
            return JsonResponse(ret)

        pt_id = request.POST.get("id")
        try:
            pt_obj = PeriodicTask.objects.get(id__exact=int(pt_id))
        except PeriodicTask.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "PeriodicTask 模型中不存在 id: %s 的对象, 请刷新重试..." % (pt_id)
            return JsonResponse(ret)

        task_update_form = TaskUpdateForm(request.POST)
        if not task_update_form.is_valid():
            ret["result"] = 1
            error_msg = json.loads(task_update_form.errors.as_json(escape_html=False))
            ret["msg"] = '\n'.join([i["message"] for v in error_msg.values() for i in v])
            return JsonResponse(ret)

        if request.POST.get("expires"):
            pt_obj.expires = datetime.strptime(request.POST.get("expires"), '%Y/%m/%d %H:%M')

        if task_update_form.cleaned_data.get("schedule") == 'crontab':
            pt_obj.crontab = task_update_form.cleaned_data.get("crontab")
            pt_obj.interval = None
        else:
            pt_obj.interval = task_update_form.cleaned_data.get("interval")
            pt_obj.crontab = None

        try:
            pt_obj.task = task_update_form.cleaned_data.get("task")
            pt_obj.description = task_update_form.cleaned_data.get("description")
            pt_obj.args = task_update_form.cleaned_data.get("args")
            pt_obj.kwargs = task_update_form.cleaned_data.get("kwargs")
            pt_obj.enabled = task_update_form.cleaned_data.get("enabled")
            pt_obj.save(update_fields=["task","description","args","kwargs","enabled","interval","crontab","expires"])
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "PeriodicTask 更新对象 ID: %s 失败，请查看日志..." %(pt_id)
            wslog_error().error("PeriodicTask 更新对象 ID: %s 失败, 错误信息: %s" % (pt_id,e.args))
        else:
            ret["msg"] = "更新 PeriodicTask 对象成功"
        return JsonResponse(ret)

class TaskDeleteView(LoginRequiredMixin,View):
    permission_required = "djcelery.delete_periodictask"

    def post(self,request):
        ret = {"result":0}
    
        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有'删除定时任务'的权限,请联系运维!"
            return JsonResponse(ret)

        pt_id = request.POST.get("id")
        try:
            pt_obj = PeriodicTask.objects.get(id__exact=pt_id)
            pt_obj.delete()
        except PeriodicTask.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "PeriodicTask 模型不存在 id: %s 的对象,请刷新重试" % (pt_id)
            return JsonResponse(ret)
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "PeriodicTask 模型删除 id: %s 的对象失败,请查看日志" % (pt_id)
            wslog_error().error("PeriodicTask 模型删除 id %s 的对象失败,错误信息: %s" % (pt_id, e.args))
            return JsonResponse(ret)
        else:
            ret["msg"] = "PeriodicTask 模型删除 id: %s 的对象成功" % (pt_id)

        return JsonResponse(ret)

class TaskResultListView(LoginRequiredMixin,ListView):
    model = TaskMeta
    template_name = "task_result_list.html"
    ordering = "-id"

    def get_queryset(self):
        queryset = super(TaskResultListView,self).get_queryset()
        queryset = queryset.all()[:100]
        return queryset

class TaskResultDeleteView(LoginRequiredMixin,View):
    permission_required = "djcelery.delete_taskmeta"

    def post(self,request):
        ret = {"result":0}

        if not request.user.has_perm(self.permission_required):
            ret["result"] = 1
            ret["msg"] = "Sorry,你没有'删除任务执行结果'的权限,请联系运维!"
            return JsonResponse(ret)

        tm_id = request.POST.get("id")
        try:
            tm_obj = TaskMeta.objects.get(id__exact=tm_id)
            tm_obj.delete()
        except TaskMeta.DoesNotExist:
            ret["result"] = 1
            ret["msg"] = "TaskMeta 模型不存在 id: %s 的对象,请刷新重试" % (tm_id)
            return JsonResponse(ret)
        except Exception as e:
            ret["result"] = 1
            ret["msg"] = "TaskMeta 模型删除 id: %s 的对象失败,请查看日志" % (tm_id)
            wslog_error().error("TaskMeta 模型删除 id %s 的对象失败,错误信息: %s" % (tm_id, e.args))
            return JsonResponse(ret)
        else:
            ret["msg"] = "TaskMeta 模型删除 id: %s 的对象成功" % (tm_id)

        return JsonResponse(ret)
