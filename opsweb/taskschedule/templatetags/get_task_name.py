from django import template
from django.db.models import Q
from taskschedule.models import TaskResultRecord
from dashboard.utils.wslog import wslog_error,wslog_info

register = template.Library()
@register.filter(name="get_task_name")
def get_task_name(value):
    try:
        trr_obj = TaskResultRecord.objects.get(task_id__exact=value)
    except Exception as e:
        wslog_error().error("TaskResultRecord 模型中查询 task_id: %s 失败,错误信息: %s" %(value,e.args))
        return value
    else:
        return trr_obj.task_name