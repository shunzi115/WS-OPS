from django.db import models
from resources.models import ServerModel
from workform.models import WorkFormModel
from django.contrib.auth.models import Group,User

ENV_CHOICES = (
    ("online","生产"),
    ("gray","预发布"),
)

STATUS_CHOICES = (
    ("active","启用"),
    ("stop","停用"),
)

''' 数据库集群表 '''
class DBClusterModel(models.Model):
    name = models.CharField("集群名称",unique=True, max_length=30,null=False)
    w_vip = models.GenericIPAddressField("写VIP",protocol="IPv4",null=True,blank=True)
    w_domain_name = models.CharField("写域名", max_length=100,null=True,blank=True)
    r_vip = models.GenericIPAddressField("读VIP", protocol="IPv4", null=True,blank=True)
    r_domain_name = models.CharField("读域名", max_length=100, null=True, blank=True)
    env = models.CharField("所属环境", choices=ENV_CHOICES, max_length=10, default='online', null=False)
    create_time = models.DateTimeField("创建时间",auto_now_add=True,null=True)
    last_update_time = models.DateTimeField("最近更新时间",auto_now=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "数据库集群表"
        db_table = "dbcluster"
        unique_together = ["name","env"]
        ordering = ["-id"]

''' 数据库表 '''
class DBModel(models.Model):
    name = models.CharField("数据库名称",max_length=30,null=False,unique=True)
    cluster_name = models.ManyToManyField(DBClusterModel, verbose_name='集群名称')
    db_manage_group = models.ManyToManyField(Group,verbose_name="管理组")
    create_time = models.DateTimeField("创建时间",auto_now_add=True,null=True)
    last_update_time = models.DateTimeField("最近更新时间",auto_now=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "数据库表"
        db_table = "dbs"
        ordering = ["-id"]

''' 数据库实例表 '''
class DBInstanceModel(models.Model):
    ROLE_CHOICES = (
        ("master","主库"),
        ("slave","从库"),
    )

    BACKUP_CHOICES = (
        ("yes", "是"),
        ("no", "否"),
    )
    name = models.CharField("实例名称",max_length=30, unique=True,null=False)
    ins_cluster = models.ForeignKey(DBClusterModel, verbose_name='集群名称')
    ins_ip = models.ForeignKey(ServerModel, verbose_name='实例IP')
    port = models.CharField("端口号",max_length=10, null=False)
    env = models.CharField("所属环境", choices=ENV_CHOICES, max_length=10, default='online', null=False)
    role = models.CharField("主从标识",choices=ROLE_CHOICES,max_length=10, default='slave',null=False)
    backup = models.CharField("备份标识,确定数据备份是否存在这个实例",choices=BACKUP_CHOICES,max_length=10, default='no',null=False)
    data_dir = models.CharField("数据目录",max_length=100, null=False)
    backup_dir = models.CharField("数据备份目录", max_length=100, null=True,blank=True)
    scripts = models.CharField("启动脚本",max_length=100, null=False)
    create_time = models.DateTimeField("创建时间",auto_now_add=True)
    last_update_time = models.DateTimeField("最近修改时间",auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "数据库实例表"
        db_table = "dbinstance"
        unique_together = ["name", "env"]
        ordering = ["-id"]

''' 存储 SQL块或者附件 表 '''
class SQLDetailModel(models.Model):
    SQL_STATUS_CHOICES = (
        ("0", "待执行"),
        ("1", "已执行"),
        ("2", "已回滚"),
        ("3", "暂停执行"),
        ("4", "拒绝执行"),
        ("5", "部分回滚"),
    )

    EXEC_STATUS_CHOICES = (
        ("0","执行成功"),
        ("1","执行有错误"),
        ("2", "未执行")
    )
    sql_block = models.CharField("sql语句块", max_length=20000, null=True,blank=True)
    sql_file_url = models.CharField("SQL附件的URL", max_length=1000, null=True,blank=True)
    env = models.CharField("所属环境", choices=ENV_CHOICES, max_length=10, default='online', null=False)
    status = models.CharField("状态", choices=SQL_STATUS_CHOICES, max_length=10, default='0', null=False)
    exec_status = models.CharField("执行状态", choices=EXEC_STATUS_CHOICES, max_length=10, default='2', null=False)
    db_name = models.ForeignKey(DBModel, verbose_name='数据库名')
    sql_workform = models.ForeignKey(WorkFormModel, null=True,verbose_name='关联的工单')
    exec_user = models.ForeignKey(User, null=True,verbose_name='执行人')
    create_time = models.DateTimeField("创建时间", auto_now_add=True)

    def __str__(self):
        return "%s: %s" %(self.env,self.db_name)

    class Meta:
        verbose_name = "SQL记录表"
        db_table = "sqldetail"
        ordering = ["id"]

''' SQL 语法检查临时表 '''
class SQLCheckTmpModel(models.Model):
    sql_check_uuid = models.CharField("语法检查唯一标记", max_length=50, null=False)
    sql_detail = models.CharField("sql语句", max_length=20000, null=False)
    affected_rows = models.CharField("sql语句影响的行数", max_length=10, null=False)
    errmsg = models.CharField("sql语句错误信息", max_length=1000, null=True)
    create_time = models.DateTimeField("创建时间", auto_now_add=True)

    def __str__(self):
        return self.sql_check_uuid

    class Meta:
        verbose_name = "SQL语法检查临时表"
        db_table = "sqlchecktmp"
        ordering = ["id"]

''' SQL执行的详细信息表 '''
class SQLExecDetailModel(models.Model):
    RESULT_CHOICES = (
        ("success","成功"),
        ("failed","失败"),
        ("noneed","不需要"),
        ("noexec", "未执行"),
    )

    sql = models.CharField("单条sql语句", max_length=10000, null=False)
    sql_tablename = models.CharField("sql表名", max_length=50, null=True)
    exec_result = models.CharField("sql执行结果",choices=RESULT_CHOICES,max_length=10, null=False,default="noexec")
    backup_result = models.CharField("sql备份结果", choices=RESULT_CHOICES, max_length=10, null=True)
    check_affected_rows = models.CharField("sql检查影响的行数", max_length=100, null=True)
    affected_rows = models.CharField("sql执行影响的行数", max_length=100, null=True)
    errormessage = models.CharField("sql执行错误信息", max_length=500, null=True)
    backup_dbname = models.CharField("备份的库名",max_length=100, null=True)
    sql_block = models.ForeignKey(SQLDetailModel, verbose_name='关联的sql块或文件')
    execute_time = models.CharField("sql执行时间",max_length=50, null=True)
    seqnum = models.CharField("sql执行序列号",max_length=100, null=True)
    sql_sha1 = models.CharField("sql的sha1",max_length=100, null=True)
    create_time = models.DateTimeField("创建时间", auto_now_add=True)
    last_update_time = models.DateTimeField("最近修改时间", auto_now=True)

    def __str__(self):
        return self.sql

    class Meta:
        verbose_name = "SQL执行结果表"
        db_table = "sqlexec_detail"
        ordering = ["id"]

''' SQL回滚语句及详情表 '''
class SQLRollBackModel(models.Model):
    RESULT_CHOICES = (
        ("success","成功"),
        ("failed","失败"),
        ("noneed","不需要"),
        ("noexec", "未执行"),
    )
    sql_rollback = models.CharField("sql的回滚语句", max_length=10000, null=True)
    rollback_check_affected_rows = models.CharField("sql检查影响的行数", max_length=100, null=True)
    rollback_backup_dbname = models.CharField("备份的库名",max_length=100, null=True)
    sql_already_exec = models.ForeignKey(SQLExecDetailModel, verbose_name='关联已执行的SQL语句')
    rollback_execute_time = models.CharField("sql执行时间",max_length=50, null=True)
    rollback_seqnum = models.CharField("sql执行序列号",max_length=100, null=True)
    sql_rollback_result = models.CharField("sql回滚结果",choices=RESULT_CHOICES,max_length=10, null=False,default="noexec")
    rollback_affected_rows = models.CharField("sql执行回滚影响的行数", max_length=100, null=True)
    rollback_errmsg = models.CharField("sql回滚错误信息", max_length=500, null=True)
    rollback_exec_user = models.ForeignKey(User, null=True, verbose_name='执行人')
    create_time = models.DateTimeField("创建时间", auto_now_add=True)
    last_update_time = models.DateTimeField("最近修改时间", auto_now=True)

    def __str__(self):
        return self.sql_rollback

    class Meta:
        verbose_name = "SQL回滚语句表"
        db_table = "sql_rollback"
        ordering = ["id"]

''' Inception 后台管理 '''
class InceptionBackgroundModel(models.Model):
    inc_ip = models.GenericIPAddressField("Inception 服务器IP",protocol="IPv4",null=False)
    inc_port = models.CharField("Inception 服务器端口", max_length=5, null=False)
    inc_backup_ip = models.GenericIPAddressField("Inception 备份服务器IP",protocol="IPv4",null=True,blank=True)
    inc_backup_port = models.CharField("Inception 备份服务器端口", max_length=5, null=True,blank=True)
    inc_backup_username = models.CharField("Inception 备份服务器账号",max_length=50, null=True,blank=True)
    inc_backup_password = models.CharField("Inception 备份服务器密码",max_length=100, null=True,blank=True)
    inc_status = models.CharField("Inception 配置状态", choices=STATUS_CHOICES, max_length=10, null=False,default="stop")
    create_time = models.DateTimeField("创建时间", auto_now_add=True)
    last_update_time = models.DateTimeField("最近修改时间", auto_now=True)

    def __str__(self):
        return "%s: %s" %(self.inc_ip,self.inc_port)

    class Meta:
        verbose_name = "Inception 后台管理表"
        db_table = "inception_background_manage"
        unique_together = ["inc_ip","inc_port"]
        ordering = ["id"]

''' Inception 自定义高危SQL '''
class InceptionDangerSQLModel(models.Model):
    sql_keyword = models.CharField("高危SQL关键字",max_length=5000, null=False)
    status = models.CharField("该规则是否启用", choices=STATUS_CHOICES, max_length=10, null=False, default="stop")
    create_time = models.DateTimeField("创建时间", auto_now_add=True)
    last_update_time = models.DateTimeField("最近修改时间", auto_now=True)

    def __str__(self):
        return self.sql_keyword

    class Meta:
        verbose_name = "Inception 自定义高危SQL"
        db_table = "inception_danger_sql"
        ordering = ["id"]