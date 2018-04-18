from django.db import models
from djcelery.models import TaskMeta


class TaskResultRecord(models.Model):
    task_name = models.CharField("task 名称",max_length=500,null=False)
    task_id = models.CharField("task id",max_length=500,null=False)

    def __str__(self):
        return "%s: %s" %(self.task_name,self.task_id)

    class Meta:
        verbose_name = "task_name 与 task_id 映射表"
        db_table = "task_result_record"
        ordering = ["-id"]