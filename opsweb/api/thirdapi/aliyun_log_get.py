import time
from aliyun.log.logitem import LogItem
from aliyun.log.logclient import LogClient
from aliyun.log.getlogsrequest import GetLogsRequest
from aliyun.log.putlogsrequest import PutLogsRequest
from aliyun.log.listlogstoresrequest import ListLogstoresRequest
from aliyun.log.gethistogramsrequest import GetHistogramsRequest
import json

def main():

    # 日志 Project 所属区域匹配的 Endpoint
    endpoint = 'cn-beijing-intranet.log.aliyuncs.com'

    # 访问阿里云密钥 AccessKeyId
    accessKeyId = '**********'

    # 访问阿里云密钥 AccessKeySecret
    accessKey = '****************************'

    # 日志的 project 项目名称
    project = 'java-applications'

    # 日志库名称
    logstore = 'mop_log'

    # 构建一个 client
    client = LogClient(endpoint, accessKeyId, accessKey)

    # 列出所有的 logstore
    req1 = ListLogstoresRequest(project)
    res1 = client.list_logstores(req1)
    res1.log_print()
    topic = "mop"
    query = "/ask/article/list or /ask/article/get"
    From = int(time.time()) - 600
    To = int(time.time())
    res3 = None

    # 查询最近10分钟内，满足query条件的日志条数，如果执行结果不是完全正确，则进行重试
    while (res3 is None) or (not res3.is_completed()):
        req3 = GetHistogramsRequest(project, logstore, From, To, topic, query)
        res3 = client.get_histograms(req3)
    res3.log_print()
    print(type(res3.log_print()))

    '''
    # 获取满足query的日志条数
    total_log_count = res3.get_total_count()
    log_line = 10

    # 每次读取10条日志，将日志数据查询完，对于每一次查询，如果查询结果不是完全准确，则重试3次
    for offset in range(0, total_log_count, log_line):
        res4 = None
        for retry_time in range(0, 3):
            req4 = GetLogsRequest(project, logstore, From, To, topic, query, log_line, offset, False)
            res4 = client.get_logs(req4)
            if res4 is not None and res4.is_completed():
                break
            time.sleep(1)
        if res4 is not None:
            res4.log_print()
            print("*" * 20)
            print(json.loads(res4.log_print()))
            print(type(res4.log_print()))
    '''

if __name__ == '__main__':
    main()
