from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from dashboard.utils.wslog import wslog_error,wslog_info
from opsweb.settings import EMAIL_HOST_USER

def mail_send(subject,message,mail_to,html_content=None):
    try:
        send_mail(subject,message,EMAIL_HOST_USER,mail_to,fail_silently=False,html_message=html_content)
    except Exception as e:
        wslog_error().error("邮件: '%s' 发送失败,错误信息: %s" %(subject,e.args))
    else:
        wslog_info().info("邮件: '%s' 发送成功" %(subject))

def mail_send_html(subject,message,mail_to,html_content=None):
    ''' 如果html_content 为None 则邮件不能发送, 而上面那种方式则不会 '''
    try:
        m = EmailMultiAlternatives(subject,message,EMAIL_HOST_USER,mail_to)
        m.attach_alternative(html_content, "text/html")
        m.send()
    except Exception as e:
        wslog_error().error("邮件: '%s' 发送失败,错误信息: %s" %(subject,e.args))
    else:
        wslog_info().info("邮件: '%s' 发送成功" %(subject))

if __name__ == '__main__':
    mail_send("过去的过不去的","一年又过了一年",['haha@163.com'])
    
