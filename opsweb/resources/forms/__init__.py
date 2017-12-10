from django import forms
from resources.models import IDC,Server_Aliyun


class IdcAddForm(forms.Form):
    name = forms.CharField(required=True,error_messages={"required":"简称不能为空"})
    cn_name = forms.CharField(required=True,error_messages={"required":"中文名不能为空"})
    user = forms.CharField(required=True,error_messages={"required":"联系人不能为空"})
    phone = forms.CharField(required=True,error_messages={"required":"电话不能为空"})
    email = forms.EmailField(required=False)
    address = forms.CharField(required=True,error_messages={"required":"地址不能为空"})

    def clean_name(self):
        name = self.cleaned_data.get("name")
        try:
            IDC.objects.get(name__exact=name)
        except IDC.DoesNotExist:
            return name
        except Exception as e:
            raise forms.ValidationError(e.args)
        else:
            raise forms.ValidationError("IDC 简称已经存在")

class ServerAliyunAddForm(forms.Form):
    private_ip = forms.GenericIPAddressField(required=True,protocol="IPv4",error_messages={"required":"IP地址不能为空","invalid":"IPv4地址无效"})
    ssh_port = forms.CharField(required=True,max_length=5,error_messages={"required":"SSH端口不能为空","max_length":"SSH端口不能超过5位数字"})
    idc = forms.IntegerField(required=True)
    env = forms.ChoiceField(required=True,choices=Server_Aliyun.ENV_CHOICES,error_messages={"required":"必须选择一个环境"})

    def clean_private_ip(self):
        private_ip = self.cleaned_data.get("private_ip")
        try:
            Server_Aliyun.objects.get(private_ip__exact=private_ip)
        except Server_Aliyun.DoesNotExist:
            return private_ip
        except Exception as e:
            raise forms.ValidationError("该IP已经存在，不需要添加")

    def clean_ssh_port(self):
        ssh_port = self.cleaned_data.get("ssh_port")
        if int(ssh_port) >= 65535:
            raise forms.ValidationError("SSH端口必须小于65535")
        return ssh_port

    def clean_idc(self):
        idc_id = self.cleaned_data.get("idc")
        try:
            idc_obj = IDC.objects.get(id__exact=int(idc_id))
        except IDC.DoesNotExist:
            raise forms.ValidationError("IDC 不存在")
        else:
            return idc_obj
