from django.http import JsonResponse
from django.views.generic import TemplateView,ListView,View
from dashboard.utils.wslog import wslog_error,wslog_info
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms.models import model_to_dict
from celery.task.control import inspect
from itertools import chain
from djcelery.models import CrontabSchedule,IntervalSchedule,PeriodicTask

class GetTaskView(LoginRequiredMixin,View):
    def get(self,request):
        i_obj = inspect()
        try:
            registered_tasks_list = list(set(chain.from_iterable(i_obj.registered_tasks().values())))
        except Exception as e:
            registered_tasks_list = []
            wslog_error().error("通过 api 接口获取 注册的task信息失败,错误信息: %s" %(e.args))
        return JsonResponse(registered_tasks_list,safe=False)

class GetCrontabView(LoginRequiredMixin,View):
    def get(self,request):
        try:
            crontab_list = [{"id":cs_obj.id,"crontabs_str":"%s %s %s %s %s -- (分/时/日/月/周/)" %(cs_obj.minute,\
                                                                                cs_obj.hour,\
                                                                                cs_obj.day_of_month,\
                                                                                cs_obj.month_of_year,\
                                                                                cs_obj.day_of_week)} \
                                                                                for cs_obj in CrontabSchedule.objects.all()]
        except Exception as e:
            crontab_list = []
            wslog_error().error("通过 api 接口获取 crontab调度信息失败,错误信息: %s" %(e.args))
        return JsonResponse(crontab_list,safe=False)

class GetIntervalView(LoginRequiredMixin,View):
    def get(self,request):
        try:
            interval_list = [{"id":is_obj.id,"intervals_str":"%s %s" %(is_obj.every,is_obj.period)} \
                                                                        for is_obj in IntervalSchedule.objects.all()]
        except Exception as e:
            interval_list = []
            wslog_error().error("通过 api 接口获取 interval 调度信息失败,错误信息: %s" %(e.args))
        return JsonResponse(interval_list,safe=False)
