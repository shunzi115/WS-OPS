#!/usr/bin/env python
#coding=utf-8
#此 api 是用来获取 ecs 列表


from aliyunsdkcore import client
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkecs.request.v20140526 import DescribeInstancesRequest
from aliyunsdkecs.request.v20140526 import DescribeInstanceAutoRenewAttributeRequest
from dashboard.utils.get_ws_conf import get_myconf
from dashboard.utils.wslog import wslog_error,wslog_info
import json
import os

aliyun_conf = get_myconf(section="aliyun_config")

if aliyun_conf["result"] == 0:
    accessKeyId = aliyun_conf["mysec_conf"]["haha"]
    accessSecret = aliyun_conf["mysec_conf"]["hehe"]
else:
    wslog_error().error(aliyun_conf["msg"])
    accessKeyId = ''
    accessSecret = ''

# 获取ECS所有实例或者指定实例的所有信息
def AliyunDescribeInstances(**kwargs):

    clt = client.AcsClient(accessKeyId,accessSecret,'cn-hangzhou')

    # 设置参数
    request = DescribeInstancesRequest.DescribeInstancesRequest()
    request.set_accept_format('json')

    request.add_query_param('RegionId', 'cn-beijing')
    request.add_query_param('PageSize', 100)

    if kwargs:
        for k,v in kwargs.items():
            request.add_query_param(k, v)

    # 发起请求
    try:
        response = clt.do_action_with_exception(request)
    except Exception as e:
        wslog_error().error(e)
    else:
        return json.loads(response)["Instances"]["Instance"]


# 获取ECS是否是自动续费
def AliyunDescribeInstanceAutoRenewAttribute(instance_id):

    clt = client.AcsClient(accessKeyId,accessSecret,'cn-hangzhou')
    request = DescribeInstanceAutoRenewAttributeRequest.DescribeInstanceAutoRenewAttributeRequest()
    request.set_accept_format('json')

    request.add_query_param('InstanceId', instance_id)
    request.add_query_param('RegionId', 'cn-beijing')
    ret = {"result":0,"msg":None}

    # 发起请求
    try:
        response = clt.do_action_with_exception(request)
    except ServerException as e:
        ret["result"] = 1
        wslog_error().error(e)
    else:
        ret["data"] = json.loads(response)['InstanceRenewAttributes']['InstanceRenewAttribute'][0]['RenewalStatus']
    return ret

if __name__ == "__main__":
    result = AliyunDescribeInstances()
    ecs_list = [i["NetworkInterfaces"]["NetworkInterface"][0]["PrimaryIpAddress"] for i in result]

