from api.thirdapi import zabbix_api
from opsweb.celery import app
from celery import shared_task
from celery.utils.log import get_task_logger
from dashboard.utils.get_local_ip import get_ip_address
import requests
from requests import ConnectionError
import sys
from publish.tasks import dingding_msg_send,wx_msg_send

celery_log_info = get_task_logger("info_logger")
celery_log_error = get_task_logger("error_logger")

@shared_task(bind=True,name="ZabbixHostSyncCrontab")
def ZabbixHostSyncCrontab(self):
    zabbix_api.ZabbixHostAutoSync()    

@shared_task(bind=True,name="HealthCheckCrontab")
def HealthCheckCrontab(self):
    nginx_ip = get_ip_address('eth0')
    nginx_port = '9999'
    health_check_url = "http://%s:%s/healthcheck" %(nginx_ip,nginx_port)
    r_args = args={"format":"json"}
    try:
        r = requests.get(health_check_url, params=r_args)
    except ConnectionError:
        celery_log_error.error("请求健康检查地址 %s 失败，请检查URL地址和端口是否正确" % (health_check_url))
        sys.exit()
    except Exception as e:
        celery_log_error.error("请求健康检查地址 %s 失败，错误日志: %s" % (health_check_url,e.args))
        sys.exit()

    if r.status_code != requests.codes.ok:
        celery_log_error.error("请求健康检查地址 %s 失败，请检查URI是否正确" % (r.url))
        sys.exit()

    try:
        health_check_list = r.json()['servers']['server']
        health_check_fail_list = [ hc for hc in health_check_list if hc["status"] == 'down']
    except Exception as e:
        celery_log_error.error("过滤健康检查结果失败，错误日志: %s" % (e.args))
        sys.exit()
    if health_check_fail_list:
        for hcf in health_check_fail_list:
            dingding_fail_msg = {"title":"应用: %s 健康检查失败" %(hcf["upstream"]),\
                                 "text": "检查方式：%s\n检查地址：%s\n检查状态：%s" %(hcf["type"],hcf["name"],hcf["status"]),\
                                 "messageUrl":"http://39.106.70.239:9999/healthcheck",\
                                 "picUrl": "http://39.106.70.239:8888/static/img/failed_2.png"}
            dingding_msg_send.delay(dingding_fail_msg,type="monitor")


