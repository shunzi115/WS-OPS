from dashboard.utils.get_ws_conf import get_myconf
from dashboard.utils.wslog import wslog_error,wslog_info
import  requests,json

dingding_conf = get_myconf(section="dingding_config")

if dingding_conf["result"] == 0:
    webhook = dingding_conf["mysec_conf"]["webhook"]
    webhook_monitor = dingding_conf["mysec_conf"]["webhook_monitor"]
else:
    webhook = ''
    webhook_monitor = ''

class DingDingMsgSend(object):
    # 钉钉机器人配置，参考：https://open-doc.dingtalk.com/docs/doc.htm?spm=a219a.7629140.0.0.karFPe&treeId=257&articleId=105735&docType=1
    def __init__(self):
        self.webhook = webhook
        self.webhook_monitor = webhook_monitor

    def msg_post(self,send_data,webhook_addr):
        headers = {'Content-Type': 'application/json'}
        r = requests.post(webhook_addr, data=json.dumps(send_data), headers=headers)
        if int(json.loads(r.content)["errcode"]) == 0:
            wslog_info().info("钉钉机器人消息 发送 成功")
        else:
            wslog_error().error("钉钉机器人消息 发送 失败,错误信息: %s" % (json.loads(r.content)["errmsg"]))

    def send_dingding_text(self,data,type=None):
        # data格式：字符串
        send_data = {"msgtype": "text",
                "text": {
                    "content": data
                    }
                }
        if type:
            self.msg_post(send_data,self.webhook_monitor)
        else:
            self.msg_post(send_data,self.webhook)

    def send_dingding_markdown(self,data,type=None):
        # data格式：{title":"","text": ""}，其中 title 和 text 的内容接受 markdown 格式
        send_data = {"msgtype": "markdown",
                    "markdown": data
                }
        if type:
            self.msg_post(send_data,self.webhook_monitor)
        else:
            self.msg_post(send_data,self.webhook)

    def send_dingding_link(self,data,type=None):
        # data格式：{"title":"","text": "","messageUrl":"点击消息的链接","picUrl": "消息左侧图片的地址"}
        send_data = {"msgtype": "link",
                    "link": data
                }
        if type:
            self.msg_post(send_data,self.webhook_monitor)
        else:
            self.msg_post(send_data,self.webhook)

if __name__ == '__main__':
    #send_dingding_markdown({"title":"应用发布：**mop**","text": "### 应用发布：**mop**\n#### 发布 IP：**172.17.134.23**\n#### 发布人：**你猜猜**\n#### 发布结果：![](http://39.106.70.239:8888/static/img/success.png)\n#### 发布时间：**公元前22012年**\n#### [发布详情](http://39.106.70.239:9999/publish/list/)\n"})
    dd = DingDingMsgSend()
    dd.send_dingding_link({"title":"应用发布：mop","text": "发布 IP：172.17.134.23\n发布人：你猜猜\n发布时间：公元前22012年\n","messageUrl":"http://39.106.70.239:9999/publish/list/","picUrl": "http://39.106.70.239:8888/static/img/failed_2.png"})
