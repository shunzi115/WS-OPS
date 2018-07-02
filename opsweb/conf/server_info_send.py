#!/usr/bin/env python
# coding=utf8

from ansible_adhoc import ansible_adhoc
import logging
import requests
import sys
import json

reload(sys)
sys.setdefaultencoding('utf8')

def log_write():
    format = '%(asctime)s-[%(levelname)s]-%(message)s'
    log_format = logging.Formatter(format)
    log_handler = logging.FileHandler('/opt/zp/server_info_post.log',encoding='utf8')
    log_handler.setFormatter(log_format)
    mylog_logger = logging.getLogger('server_info')
    mylog_logger.handlers = []
    mylog_logger.addHandler(log_handler)
    mylog_logger.setLevel(logging.INFO)
    return mylog_logger

def ServerInfoFromAnsible(private_ip):
    ret = {"result":0}
    data = {}    

    try:
        server_info_ansible = ansible_adhoc('setup','gather_subset=hardware,!facter',private_ip)[private_ip]['ansible_facts']
    except Exception as e:
        ret["result"] = 1
        log_write().error("ansible api 调用失败 %s,错误信息: %s" %(private_ip,e))
        return ret

    try:
	server_idrac_ip = ansible_adhoc('shell','/usr/bin/ipmitool lan print 1 | grep "IP Address"| grep -Eo "10.82.40.[0-9]{1,3}"',private_ip)[private_ip]['stdout']
    except Exception as e:
	log_write().error("ansible api 获取 idrac_ip 失败 %s,错误信息: %s" %(private_ip,e))
	server_idrac_ip = '0.0.0.0'
   
    try:
	data["private_ip"] = private_ip
	data["hostname"] = server_info_ansible['ansible_hostname']
	data["server_brand"] = server_info_ansible['ansible_system_vendor']
	data["os_version"] = ' '.join((server_info_ansible['ansible_distribution'],server_info_ansible['ansible_distribution_version']))
	data["server_brand"] = server_info_ansible['ansible_system_vendor']
	data["server_model"] = server_info_ansible['ansible_product_name']
	data["cpu_count"] = '%s 核' %(server_info_ansible['ansible_processor_vcpus'])
	data["sn_code"] = server_info_ansible['ansible_product_serial']
	data["idrac_ip"] = server_idrac_ip
	data["swap"] = '%.2f GB' %(server_info_ansible['ansible_swaptotal_mb']/1024.0)
	data["mem"] = '%.2f GB' %(server_info_ansible['ansible_memtotal_mb']/1024.0)
	data["disk"] = '</br>'.join(['['+i+'] '+': '+server_info_ansible['ansible_devices'][i]['size'] for i in server_info_ansible['ansible_devices'] if 'ss' in i or 'sd' in i or 'vd' in i])
	data["disk_mount"] = '\n'.join(['['+i['mount']+'] '+' - '+i['device']+' : %.2f GB' %(i['size_total']/1024.0/1024.0/1024.0) for i in server_info_ansible['ansible_mounts'] if i['device'].startswith('/dev')])

    except Exception as e:
	ret["result"] = 1
	log_write().error("ansible api 获取 %s 某个属性值失败,错误信息: %s" %(private_ip,e))
    else:
	log_write().info("ansible api 获取 %s 属性成功" %(private_ip))
	ret["server_info"] = data
    return ret

def ServerInfoSend(data):
    url = "http://172.17.134.23/resources/server/idc/refresh/"
    r = requests.post(url, data=data)
    return json.loads(r.content)

if __name__ == "__main__":
    server_hosts = ["10.82.40.81","10.82.40.82","10.82.40.80","10.82.40.79","10.82.40.202","10.82.40.203","10.82.40.204","10.82.40.205","10.82.40.206","10.82.40.207","10.82.40.208","10.82.40.209","10.82.40.210","10.82.40.211","10.82.40.139","10.82.40.143","10.82.40.144","10.82.40.142","10.82.40.140","10.82.40.141","10.82.40.145","10.82.40.146","10.82.40.147","10.82.40.148","10.82.40.149","10.82.40.76","10.82.40.78"]

    for server in server_hosts:

        data = ServerInfoFromAnsible(server)
        if data["result"] == 0:
	    del data["result"]
	    data = data["server_info"]
	    r = ServerInfoSend(data)
	    if int(r["result"]) == 0:
	        log_write().info("服务器 %s 信息 post 成功" %(data["private_ip"]))
	    else:
	        log_write().error("服务器 %s 信息 post 失败,错误信息: %s" %(data["private_ip"],r["msg"]))
		continue
	else:
	    continue
