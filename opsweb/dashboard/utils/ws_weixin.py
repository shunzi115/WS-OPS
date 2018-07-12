from dashboard.utils.get_ws_conf import get_myconf
from dashboard.utils.wslog import wslog_error,wslog_info
import  requests,json

wx_conf = get_myconf(section="weixin_api_config")

if wx_conf["result"] == 0:
    wx_url = wx_conf["mysec_conf"]["wx_url"]
else:
    wx_url = ''

def WxMsgSend(send_data):
    r = requests.post(wx_url, data=send_data)
    if r.content.decode('utf8') == 'OK':
        wslog_info().info("微信消息 发送 成功")
    else:
        wslog_error().error("微信消息 发送 失败,错误信息: %s" % (json.loads(r.content)["errmsg"]))

if __name__ == '__main__':
    data = {"title":"应用 发布: haha","content":"发布 IP: 192.168.0.67 <br>发布人: 皇阿 玛 <br>发布时间: 2018-03-27 22:55:12","url":"192.168.0.66/publish/list/"}
    WxMsgSend(data)
