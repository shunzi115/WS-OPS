from opsweb.celery import app
from dashboard.utils.wslog import wslog_error,wslog_info
from celery.utils.log import get_task_logger
from celery import shared_task

log_celery = get_task_logger("info_logger")

# @app.task(bind=True,name="hello")
def hello(self,name,where):
    log_celery.info("task_name: %s task_id: %s hello %s welcome to %s" %(self.name,self.request.id,name,where))

# @shared_task(bind=True,name="haha")
def haha_add(self,x,y):
    log_celery.info("the result is 7")
    return x + y
