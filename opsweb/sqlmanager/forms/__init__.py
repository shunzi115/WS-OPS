from django import forms
from django.forms import ModelForm
from sqlmanager.models import DBInstanceModel,DBClusterModel,DBModel,SQLExecDetailModel,SQLDetailModel,InceptionBackgroundModel,InceptionDangerSQLModel
import os

class DBClusterAddForm(ModelForm):
    class Meta:
        model = DBClusterModel
        fields = ["name","w_vip","r_vip","w_domain_name","r_domain_name","env"]
        error_messages = {
            "name" : {
                "required": "'名称'不能为空",
                "max_length": "'名称'字符串长度必须小于30",
            },
            "env": {
                "required": "必选选择一个环境",
            },
        }

    def clean_w_vip(self):
        w_vip = self.cleaned_data.get("w_vip")
        if w_vip:
            try:
                DBClusterModel.objects.get(w_vip__exact=w_vip)
            except DBClusterModel.DoesNotExist:
                return w_vip
            else:
                raise forms.ValidationError("该 VIP 已经配置在其他集群中，请修改其他VIP")

    def clean_r_vip(self):
        r_vip = self.cleaned_data.get("r_vip")
        if r_vip:
            try:
                DBClusterModel.objects.get(r_vip__exact=r_vip)
            except DBClusterModel.DoesNotExist:
                return r_vip
            else:
                raise forms.ValidationError("该 VIP 已经配置在其他集群中，请修改其他VIP")

class DBClusterChangeForm(DBClusterAddForm):
    class Meta(DBClusterAddForm.Meta):
        exclude = ["name"]

    def clean_r_vip(self):
        r_vip = self.cleaned_data.get("r_vip")
        return r_vip

    def clean_w_vip(self):
        w_vip = self.cleaned_data.get("w_vip")
        return w_vip

class DBAddForm(ModelForm):
    class Meta:
        model = DBModel
        fields = ["name","cluster_name","db_manage_group"]
        error_messages = {
            "name" : {
                "required": "'名称'不能为空",
                "max_length": "'名称'字符串长度必须小于30",
            },
            "cluster_name": {
                "required": "'所属集群'不能为空",
            },
            "db_manage_group": {
                "required": "'所属组'不能为空",
            },
        }

class DBChangeForm(DBAddForm):
    class Meta(DBAddForm.Meta):
        exclude = ["name"]

class DBInstanceAddForm(ModelForm):
    class Meta:
        model = DBInstanceModel
        fields = ["name","ins_cluster","ins_ip","port","role","backup","scripts","data_dir","backup_dir","env"]
        error_messages = {
            "name" : {
                "required": "'名称'不能为空",
                "max_length": "'名称'字符串长度必须小于30",
            },
            "ins_cluster": {
                "required": "'所属集群'不能为空",
            },
            "ins_ip": {
                "required": "'实例IP'不能为空",
            },
            "port": {
                "required": "'实例端口'不能为空",
                "max_length": "'实例端口'字符串长度必须小于10",
            },
            "role": {
                "required": "'实例主从标识'不能为空",
            },
            "backup": {
                "required": "'实例备份标识'不能为空",
            },
            "env": {
                "required": "'所属环境'不能为空",
            },
            "scripts": {
                "required": "'实例启动脚本'不能为空",
                "max_length": "'实例启动脚本'字符串长度必须小于100",
            },
            "data_dir": {
                "required": "'实例数据目录'不能为空",
                "max_length": "'实例数据目录'字符串长度必须小于100",
            },
            "backup_dir": {
                "max_length": "'实例备份目录'字符串长度必须小于100",
            },
        }

    def clean_port(self):
        port = self.cleaned_data.get("port")
        try:
            port_int = int(port)
        except Exception as e:
            raise forms.ValidationError("端口号必须是介于1-65535之间的数字")

        if port_int > 65535 or port_int < 1:
            raise forms.ValidationError("端口号必须介于1-65535之间")
        else:
            return port

    def clean_data_dir(self):
        data_dir = self.cleaned_data.get("data_dir")
        if not os.path.isabs(data_dir):
            raise forms.ValidationError("请输入正确的文件路径，以斜线/开头")
        return data_dir

    def clean_backup_dir(self):
        backup = self.cleaned_data.get("backup")
        backup_dir = self.cleaned_data.get("backup_dir")
        if backup == 'yes':
            if not backup_dir:
                raise forms.ValidationError("既然指定是备份服务器，必须填写备份目录")
            if not os.path.isabs(backup_dir):
                raise forms.ValidationError("请输入正确的文件路径，以斜线/开头")
        else:
            if backup_dir:
                raise forms.ValidationError("既然不是是备份服务器，无需填写备份目录")

        return backup_dir

class DBInstanceChangeForm(DBInstanceAddForm):
    class Meta(DBInstanceAddForm.Meta):
        exclude = ["name"]

class SQLDetailAddForm(ModelForm):
    class Meta:
        model = SQLDetailModel
        fields = ["sql_block","env","db_name","sql_file_url"]
        error_messages = {
            "sql_block" : {
                "max_length": "'SQL语句'字符串长度必须小于20000",
            },
            "sql_file_url": {
                "max_length": "所有'SQL附件'名称字符串总长度必须小于1000",
            },
            "env": {
                "required": "必须选择'环境'",
            },
            "db_name": {
                "required": "必须选择'Mysql 库名'",
            },
        }

    def clean(self):
        cleaned_data = self.cleaned_data
        if self.is_valid():
            if cleaned_data.get('sql_block') and cleaned_data.get('sql_file_url'):
                raise forms.ValidationError("只能在左侧 '填写SQL' 或 '上传SQL附件',二者只能选其一...")
            elif cleaned_data.get('sql_block') or cleaned_data.get('sql_file_url'):
                return cleaned_data
            else:
                raise forms.ValidationError("必须在左侧 '填写SQL' 或 '上传SQL附件'...")

class InceptionBackgroundAddForm(ModelForm):
    class Meta:
        model = InceptionBackgroundModel
        fields = ["inc_ip","inc_port","inc_backup_ip","inc_backup_port","inc_backup_username","inc_backup_password","inc_status"]

    def clean_inc_port(self):
        inc_port = self.cleaned_data.get("inc_port")
        if int(inc_port) >= 65535 or int(inc_port) < 1:
            raise forms.ValidationError("端口必须在 1-65535 之间")
        return inc_port

    def clean_inc_status(self):
        inc_status = self.cleaned_data.get("inc_status")
        if inc_status == 'active' and InceptionBackgroundModel.objects.get(inc_status__exact="active"):
            raise forms.ValidationError("Inception 只能存在一个处于 '激活' 状态的服务器")
        return inc_status

class InceptionBackgroundChangeForm(InceptionBackgroundAddForm):
    class Meta(InceptionBackgroundAddForm.Meta):
        exclude = ["inc_port","inc_status"]

class InceptionDangerSQLAddForm(ModelForm):
    class Meta:
        model = InceptionDangerSQLModel
        fields = ["sql_keyword","status"]
