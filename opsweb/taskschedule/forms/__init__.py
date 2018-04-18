from django import forms
from djcelery.models import CrontabSchedule,IntervalSchedule,PeriodicTask
from dashboard.utils.wslog import wslog_error,wslog_info

class CrontabScheduleForm(forms.ModelForm):
    class Meta:
        model = CrontabSchedule
        fields = ["minute","hour","day_of_month","month_of_year","day_of_week"]
        error_messages = {
            "minute" : {
                "required": "必须填写 分钟",
            },
            "hour" : {
                "required": "必须填写 小时",
            },
            "day_of_month" : {
                "required": "必须填写 日期",
            },
            "month_of_year": {
                "required": "必须填写 月份",
            },
            "day_of_week": {
                "required": "必须填写 周",
            },
        }

    def clean(self):
        cleaned_data = self.cleaned_data
        try:
            CrontabSchedule.objects.get(minute__exact=cleaned_data.get("minute"),hour__exact=cleaned_data.get("hour"), \
                                        day_of_month__exact=cleaned_data.get("day_of_month"),month_of_year__exact=cleaned_data.get("month_of_year"), \
                                        day_of_week__exact=cleaned_data.get("day_of_week")\
                                        )
        except CrontabSchedule.DoesNotExist:
            return cleaned_data
        else:
            raise forms.ValidationError("已存在相同的对象，无需添加/修改...")

class IntervalScheduleForm(forms.ModelForm):
    class Meta:
        model = IntervalSchedule
        fields = ["every","period"]
        error_messages = {
            "every" : {
                "required": "必须填写 时间间隔",
            },
            "period" : {
                "required": "必须选择 时间单位",
            },
        }

    def clean(self):
        cleaned_data = self.cleaned_data
        try:
            IntervalSchedule.objects.get(every__exact=cleaned_data.get("every"),period__exact=cleaned_data.get("period"))
        except IntervalSchedule.DoesNotExist:
            return cleaned_data
        else:
            raise forms.ValidationError("已存在相同的对象，无需添加/修改...")

class TaskAddForm(forms.ModelForm):
    SCHEDULE_CHOICES = (
        ("crontab","crontab"),
        ("interval", "interval"),
    )
    schedule = forms.ChoiceField(required=True,choices=SCHEDULE_CHOICES,error_messages={"required":"必须选择一个调度策略"})
    class Meta:
        model = PeriodicTask
        fields = ["name","task","enabled","description","args","kwargs","crontab","interval"]
        error_messages = {
            "name" : {
                "required": "必须填写 名称",
            },
            "task" : {
                "required": "必须选择 task",
            },
            "enabled" : {
                "required": "必须选择 任务的状态",
            },
            "description": {
                "required": "必须填写 描述信息",
            },
            "args": {
                "required": "必须填写 参数(列表)",
            },
            "kwargs": {
                "required": "必须填写 参数(字典)",
            },
        }

        '''djcelery 的models中已做校验，所以无需下面这些验证'''
        # def clean_name(self):
        #     name = self.cleaned_data.get("name")
        #     try:
        #         pt_obj = PeriodicTask.objects.get(name__exact=name)
        #     except PeriodicTask.DoesNotExist:
        #         return name
        #     else:
        #         forms.ValidationError("PeriodicTask 模型中已存在该 name 的任务,请换一个 name")

        # def clean_crontab(self):
        #     crontab_id = self.cleaned_data.get("crontab")
        #     if crontab_id:
        #         try:
        #             cs_obj = CrontabSchedule.objects.get(id__exact=crontab_id)
        #         except CrontabSchedule.DoesNotExist:
        #             raise forms.ValidationError("CrontabSchdule 模型中不存在这个对象,请刷新重试...")
        #         else:
        #             return cs_obj
        #
        # def clean_interval(self):
        #     interval_id = self.cleaned_data.get("interval")
        #     if interval_id:
        #         try:
        #             is_obj = IntervalSchedule.objects.get(id__exact=interval_id)
        #         except IntervalSchedule.DoesNotExist:
        #             raise forms.ValidationError("IntervalSchdule 模型中不存在这个对象,请刷新重试...")
        #         else:
        #        return is_obj

        # def clean(self):
        #     cleaned_data = self.cleaned_data
        #     print("cleaned_data_form: ",cleaned_data)
        #     if self.is_valid():
        #         del cleaned_data["schedule"]
        #         return cleaned_data
                # raise forms.ValidationError("表单验证出现异常,请检查输入的值是否合法")
            # schedule_str = cleaned_data.get("schedule")
            # crontab = cleaned_data.get("crontab")
            # interval = cleaned_data.get("interval")
            # if schedule_str == 'crontab' and crontab:
            #     del cleaned_data["interval"]
            #     del cleaned_data["schedule"]
            #     return cleaned_data
            # elif schedule_str == 'interval' and interval:
            #     del cleaned_data["crontab"]
            #     del cleaned_data["schedule"]
            #     return cleaned_data
            # else:
            #     raise forms.ValidationError("请检查'调度周期' 'Crontab' 'Interval'的选择是否合法")

class TaskUpdateForm(TaskAddForm):
    class Meta(TaskAddForm.Meta):
        exclude = ["name"]