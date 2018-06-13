from django import forms
from django.forms import ModelForm
from workform.models import WorkFormModel,ApprovalFormModel,WorkFormTypeModel,ProcessModel

class PubWorkFormAddForm(ModelForm):
    class Meta:
        model = WorkFormModel
        fields = ["title","level","reason","detail","module_name","sql",'it_check']
        error_messages = {
            "title" : {
                "required": "'工单主题'不能为空",
                "max_length": "'工单主题'字符串长度必须小于100",
            },
            "level" : {
                "required": "必须选择一个'紧急程度'",
            },
            "reason" : {
                "required": "必须选择一个'上线原因'",
            },
            "detail": {
                "required": "'详情'不能为空",
                "max_length": "'详情'字符串长度必须小于800",
            },
            "module_name": {
                "required": "发布的'模块'不能为空",
                "max_length": "'模块'字符串长度必须小于500",
            },
            "sql": {
                "required": "必须选择是否存在'SQL'",
            },
        }

    def clean_title(self):
        title = self.cleaned_data.get("title")
        try:
            wf_obj = WorkFormModel.objects.get(title__exact=title)
        except WorkFormModel.DoesNotExist:
            return title
        except Exception as e:
            raise forms.ValidationError(e.args)
        else:
            raise forms.ValidationError("该 title 的工单已经存在,请重新命名title")
                
class SqlWorkFormAddForm(PubWorkFormAddForm):
    class Meta(PubWorkFormAddForm.Meta):
        exclude = ["module_name",'it_check']

class OthersWorkFormAddForm(PubWorkFormAddForm):
    class Meta(PubWorkFormAddForm.Meta):
        exclude = ["module_name","reason","sql",'it_check']

class WorkFormApprovalForm(forms.Form):
    result = forms.ChoiceField(required=True,choices=ApprovalFormModel.RESULT_CHOICES,error_messages={"required":"必须选择一个审批结果"})
    approve_note = forms.CharField(required=True,max_length=1000,error_messages={"required":"必须填写审批意见","max_length":"审批意见长度不能超过1000字符"})

class WorkFormTypeAddForm(ModelForm):
    class Meta:
        model = WorkFormTypeModel
        fields = ["name","cn_name","process_step_id"]
        error_messages = {
            "name" : {
                "required": "必须填写名称",
                "max_length": "名称长度不能超过50字符",
            },
            "cn_name" : {
                "required": "必须填写中文名",
                "max_length": "中文名长度不能超过200字符",
            },
            "process_step_id" : {
                "required": "必须选择此工单类型的流程",
                "max_length": "流程不能超过500字符",
            },
        }

    def clean_name(self):
        name = self.cleaned_data.get("name")
        try:
            wft_obj = WorkFormTypeModel.objects.get(name__exact=name)
        except WorkFormTypeModel.DoesNotExist:
            return name
        else:
            raise forms.ValidationError("该名称已经存在")

    def clean_cn_name(self):
        cn_name = self.cleaned_data.get("cn_name")
        try:
            wft_obj = WorkFormTypeModel.objects.get(cn_name__exact=cn_name)
        except WorkFormTypeModel.DoesNotExist:
            return cn_name
        else:
            raise forms.ValidationError("该中文名已经存在") 

    def clean_process_step_id(self):
        process_step_id = self.cleaned_data.get("process_step_id")
        process_step_list = process_step_id.split(' -> ')
        # 判断最后一个流程步骤有没有选择 "完成"
        if process_step_list[-1] != "60":
            raise forms.ValidationError("流程步骤必须以 '完成' 结束")
        else:
            return process_step_id

class WorkFormTypeChangeForm(WorkFormTypeAddForm):
    class Meta(WorkFormTypeAddForm.Meta):
        exclude = ["name","cn_name"]

class WorkFormProcessAddForm(ModelForm):
    class Meta:
        model = ProcessModel
        fields = ["step","approval_require"]
        error_messages = {
            "step" : {
                "required": "必须填写step中文名",
                "max_length": "名称长度不能超过50字符",
            },
            "approval_require" : {
                "required": "必须选择step的可审核人",
            },
        }

    def clean_step(self):
        step = self.cleaned_data.get("step")
        try:
            ProcessModel.objects.get(step__exact=step)
        except ProcessModel.DoesNotExist:
            return step
        else:
            raise forms.ValidationError("Step中文名已经存在,请定义其他名称")

class WorkFormProcessChangeForm(WorkFormProcessAddForm):
    class Meta(WorkFormProcessAddForm.Meta):
        exclude = ["step"]
