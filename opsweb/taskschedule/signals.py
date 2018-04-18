from celery.signals import task_prerun,task_postrun,after_task_publish,beat_init
from dashboard.utils.wslog import wslog_error,wslog_info
from django.dispatch import receiver
from taskschedule.models import  TaskResultRecord

@receiver(task_prerun,weak=False)
def task_prerun_handler(sender=None, task_id=None, task=None, **kwargs):
    trr_obj = TaskResultRecord()
    try:
        trr_obj.task_name = task.name
        trr_obj.task_id = str(task_id)
        trr_obj.save()
    except Exception as e:
        wslog_error().error("保存 task: %s 的 task_id 失败,错误信息: %s" % (self.name, e.args))