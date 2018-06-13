#!/usr/bin/env python
#coding=utf-8

from aliyunsdkcore import client
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkcdn.request.v20141111 import DescribeUserDomainsRequest
from dashboard.utils.get_ws_conf import get_myconf
from dashboard.utils.wslog import wslog_error,wslog_info
import os
import json

aliyun_conf = get_myconf(section="aliyun_config")

if aliyun_conf["result"] == 0:
    accessKeyId = aliyun_conf["mysec_conf"]["haha"]
    accessSecret = aliyun_conf["mysec_conf"]["hehe"]
else:
    wslog_error().error(aliyun_conf["msg"])
    accessKeyId = ''
    accessSecret = ''

def AliyunDescribeCdn(**kwargs):
    clt = client.AcsClient(accessKeyId,accessSecret,'cn-hangzhou')

    # 设置参数
    request = DescribeUserDomainsRequest.DescribeUserDomainsRequest()
    request.set_accept_format('json')

    # 发起请求
    response = clt.do_action_with_exception(request)

    #输出结果
    return json.loads(response)

if __name__ == '__main__':
    AliyunDescribeCdn()

