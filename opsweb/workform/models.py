from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class WorkFormBaseModel(models.Model):

    LEVEL_CHOICES = (
        (0,"重要且紧急"),
        (1,"不重要但紧急"),
        (2,"重要但不紧急"),
        (3,"不重要且不紧急"),
    )

    STATUS_CHOICES = (
        ("0","待审批"),
        ("1","审批中"),
        ("2","已完成"),
        ("3","暂停"),
        ("4","取消"),
    )

    REASON_CHOICES = (
        ("0","项目需求"),
        ("1","故障修复"),
        ("2","技术优化"),
        ("3","其他"),
    )

    title = models.CharField("工单标题",null=False,max_length=100,unique=True)
    level = models.PositiveSmallIntegerField("紧急程度",choices=LEVEL_CHOICES,null=False)
    reason = models.CharField("上线原因",choices=REASON_CHOICES,max_length=10,null=True)
    detail = models.CharField("详情",max_length=800,null=True)
    status = models.CharField("工单状态",choices=STATUS_CHOICES,max_length=10,null=False,default="0")
    applicant = models.ForeignKey(User,related_name='+',null=True,verbose_name="申请人,与用户表多对一关联")
    create_time = models.DateTimeField("工单创建时间",auto_now_add=True,null=True)
    complete_time = models.DateTimeField("工单完成时间",auto_now_add=False,null=True)

    def __str__(self):
        return self.title

    class Meta:
        abstract = True
        ordering = ["-id"]

class ProcessModel(models.Model):

    APPLICANT_CHOICES = (
        ("0","终级大boss"),
        ("1","用户所属组leader"),
        ("2","QA组"),
        ("3","OPS组"),
        ("4","用户自己"),
        ("5","指定具体某个用户"),
        ("6","雪良组"),
        ("7","君禄组"),
        ("8","华俊组"),
        ("9","无"),
    )


    step = models.CharField("流程步骤",max_length=50,null=False,unique=True)
    step_id = models.PositiveSmallIntegerField("步骤id",null=False,unique=True)
    approval_require = models.CharField("期待有审核权限的用户或组,只是一个标记,具体逻辑后端定义",choices=APPLICANT_CHOICES,max_length=10,null=False)

    def __str__(self):
        return self.step

    class Meta:
        verbose_name = "工单流程表"
        db_table = "process"
        ordering = ["step_id"]

class WorkFormTypeModel(models.Model):

    name = models.CharField("工单类型名称",null=False,max_length=50,unique=True)
    cn_name = models.CharField("工单类型中文名称",null=False,max_length=200,unique=True)
    process_step_id = models.CharField("需要执行的工单流程",null=True,max_length=500)
    
    def __str__(self):
        return self.cn_name

    class Meta:
        verbose_name = "工单类型表"
        db_table = "workform_type"

class WorkFormModel(WorkFormBaseModel):

    SQL_CHOICES = (
        ("yes","有"),
        ("no","无"),
    ) 

    type = models.ForeignKey(WorkFormTypeModel,verbose_name="工单类型,与工单类型表多对一关联",null=False)
    module_name = models.CharField("模块名称",max_length=500,null=True)
    sql = models.CharField("是否存在SQL",choices=SQL_CHOICES,max_length=10,null=False,default="no")
    database_name = models.CharField("数据库名称",max_length=200,null=True,blank=True)
    sql_detail = models.CharField("SQL语句",max_length=1000,null=True)
    sql_file_url = models.CharField("SQL附件的URL",max_length=1000,null=True)
    process_step = models.ForeignKey(ProcessModel,verbose_name="与流程步骤多对一关联",null=True)
    approver_can = models.ManyToManyField(User,related_name='+',verbose_name="与User表建立多对多关联,声明该流程步骤能审批/执行的用户集合,具体的用户集合从ApprovalFormModel的approver_can字段同步")

    class Meta:
        verbose_name = "工单列表"
        db_table = "workform"
        ordering = ["-id"]

class ApprovalFormModel(models.Model):
    RESULT_CHOICES = (
        ("0","审批/验证通过"),
        ("1","拒绝审批/执行"),
        ("2","暂停审批/执行"),
        ("3","执行/验证异常"),
    )

    approver_can = models.ManyToManyField(User,null=True,related_name='+',verbose_name="实际能审批/执行的用户集合")
    approver = models.ForeignKey(User,related_name='+',null=True,verbose_name="最终审批/执行人")
    result = models.CharField("审批/执行结果",choices=RESULT_CHOICES,max_length=10,null=True)
    approve_note = models.CharField("审批/执行备注",max_length=1000,null=True)
    approval_time = models.DateTimeField("审批时间",auto_now_add=False,null=True)
    workform= models.ForeignKey(WorkFormModel,verbose_name="关联发布工单记录",null=True)
    process = models.ForeignKey(ProcessModel,verbose_name="与发布流程步骤多对一关联",null=True)

    def __str__(self):
        return "%s-%s" %(self.approver,self.result)

    class Meta:
        verbose_name = "审批表"
        db_table = "approval_form"
        ordering = ["-id"]
        index_together = ["process","workform"]
