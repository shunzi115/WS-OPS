from api.thirdapi import zabbix_api
from opsweb.celery import app
from celery import shared_task


@shared_task(bind=True,name="ZabbixHostSyncCrontab")
def ZabbixHostSyncCrontab():
    zabbix_api.ZabbixHostAutoSync()    
