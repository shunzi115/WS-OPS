#!/usr/bin/env python
#coding=utf-8

from pyzabbix import ZabbixAPI
from dashboard.utils.wslog import wslog_error,wslog_info
from resources.models import ServerModel
from monitor.models import ZabbixHostModel
from dashboard.utils.get_ws_conf import get_myconf
import json
import os
import sys

zabbix_conf = get_myconf(section="zabbix_config")

if zabbix_conf["result"] == 0:
    url = zabbix_conf["mysec_conf"]["url"]
    username = zabbix_conf["mysec_conf"]["username"]
    password = zabbix_conf["mysec_conf"]["password"]
else:
    wslog_error().error(zabbix_conf["msg"])
    url = ''
    username = ''
    password = ''

zapi = ZabbixAPI(url)
zapi.login(username, password)

#print("Connected to Zabbix API Version %s" % zapi.api_version())
#zapi.host.get(output="interfaces",selectInterfaces=['ip','port']) 获取结果:{'hostid': '10257', 'interfaces': [{'ip': '10.82.40.139', 'port': '10050'}]}

def ZabbixHostAutoSync():
    zabbix_api_get_host = zapi.host.get(output=["host","status"],selectInterfaces=['ip','port'])
    for h in zabbix_api_get_host:
        z_data = {}
        z_data['hostid'] = h['hostid']
        z_data['status'] = h['status']
        z_data['host'] = h['host']
        if not h['interfaces']:
            wslog_error().error("该hostid: %s 下不存在interface" %(h['hostid']))
            continue

        h_ips = list(set([i["ip"] for i in h['interfaces']]))
        if len(h_ips) > 1 :
            wslog_error().error("该hostid: %s 下 ip 地址 %s 不唯一" %(h['hostid'],";".join(h_ips)))
            continue
    
#        if h_ips[0].startswith("10.82"):
#            wslog_error().error("该hostid: %s ip 地址 %s 不是阿里云上的IP，暂时不处理" %(h['hostid'],h_ips[0]))
#            continue
        z_data['ip'] = h_ips[0]

        try:
            s_obj = ServerModel.objects.get(private_ip__exact=z_data['ip'])
        except ServerModel.DoesNotExist:
            wslog_error().error("ServerModel 模型加不存在 IP 地址: %s 的对象" %(z_data['ip']))
            continue
    
        try:
            zh = ZabbixHostModel(**z_data)
            zh.server = s_obj
            zh.save()
        except Exception as e:
            wslog_error().error("模型 ZabbixHostModel 模型对象 %s 创建失败,错误信息: %s" %(z_data['ip'],e.args))
            continue
        else:
            wslog_info().info("模型 ZabbixHostModel 模型对象 %s 创建成功" %(z_data['ip']))
        

