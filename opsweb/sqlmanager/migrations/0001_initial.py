# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-06-13 00:10
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('workform', '0004_auto_20180612_2336'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0008_alter_user_username_max_length'),
        ('resources', '0005_auto_20180516_1102'),
    ]

    operations = [
        migrations.CreateModel(
            name='DBClusterModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30, unique=True, verbose_name='集群名称')),
                ('w_vip', models.GenericIPAddressField(blank=True, null=True, protocol='IPv4', verbose_name='写VIP')),
                ('w_domain_name', models.CharField(blank=True, max_length=100, null=True, verbose_name='写域名')),
                ('r_vip', models.GenericIPAddressField(blank=True, null=True, protocol='IPv4', verbose_name='读VIP')),
                ('r_domain_name', models.CharField(blank=True, max_length=100, null=True, verbose_name='读域名')),
                ('env', models.CharField(choices=[('online', '生产'), ('gray', '预发布')], default='online', max_length=10, verbose_name='所属环境')),
                ('create_time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')),
                ('last_update_time', models.DateTimeField(auto_now=True, null=True, verbose_name='最近更新时间')),
            ],
            options={
                'verbose_name': '数据库集群表',
                'db_table': 'dbcluster',
                'ordering': ['-id'],
            },
        ),
        migrations.CreateModel(
            name='DBInstanceModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30, unique=True, verbose_name='实例名称')),
                ('port', models.CharField(max_length=10, verbose_name='端口号')),
                ('env', models.CharField(choices=[('online', '生产'), ('gray', '预发布')], default='online', max_length=10, verbose_name='所属环境')),
                ('role', models.CharField(choices=[('master', '主库'), ('slave', '从库')], default='slave', max_length=10, verbose_name='主从标识')),
                ('backup', models.CharField(choices=[('yes', '是'), ('no', '否')], default='no', max_length=10, verbose_name='备份标识,确定数据备份是否存在这个实例')),
                ('data_dir', models.CharField(max_length=100, verbose_name='数据目录')),
                ('backup_dir', models.CharField(blank=True, max_length=100, null=True, verbose_name='数据备份目录')),
                ('scripts', models.CharField(max_length=100, verbose_name='启动脚本')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('last_update_time', models.DateTimeField(auto_now=True, verbose_name='最近修改时间')),
                ('ins_cluster', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sqlmanager.DBClusterModel', verbose_name='集群名称')),
                ('ins_ip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='resources.ServerModel', verbose_name='实例IP')),
            ],
            options={
                'verbose_name': '数据库实例表',
                'db_table': 'dbinstance',
                'ordering': ['-id'],
            },
        ),
        migrations.CreateModel(
            name='DBModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30, unique=True, verbose_name='数据库名称')),
                ('create_time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')),
                ('last_update_time', models.DateTimeField(auto_now=True, null=True, verbose_name='最近更新时间')),
                ('cluster_name', models.ManyToManyField(to='sqlmanager.DBClusterModel', verbose_name='集群名称')),
                ('db_manage_group', models.ManyToManyField(to='auth.Group', verbose_name='管理组')),
            ],
            options={
                'verbose_name': '数据库表',
                'db_table': 'dbs',
                'ordering': ['-id'],
            },
        ),
        migrations.CreateModel(
            name='SQLCheckTmpModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sql_check_uuid', models.CharField(max_length=50, verbose_name='语法检查唯一标记')),
                ('sql_detail', models.CharField(max_length=1000, verbose_name='sql语句')),
                ('affected_rows', models.CharField(max_length=10, verbose_name='sql语句影响的行数')),
                ('errmsg', models.CharField(max_length=1000, null=True, verbose_name='sql语句错误信息')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
            ],
            options={
                'verbose_name': 'SQL语法检查临时表',
                'db_table': 'sqlchecktmp',
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='SQLDetailModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sql_block', models.CharField(blank=True, max_length=20000, null=True, verbose_name='sql语句块')),
                ('sql_file_url', models.CharField(blank=True, max_length=1000, null=True, verbose_name='SQL附件的URL')),
                ('env', models.CharField(choices=[('online', '生产'), ('gray', '预发布')], default='online', max_length=10, verbose_name='所属环境')),
                ('status', models.CharField(choices=[('0', '待执行'), ('1', '已执行'), ('2', '已回滚'), ('3', '暂停执行'), ('4', '拒绝执行')], default='0', max_length=10, verbose_name='状态')),
                ('exec_status', models.CharField(choices=[('0', '执行成功'), ('1', '执行有错误，需手动执行'), ('2', '未执行')], default='2', max_length=10, verbose_name='执行状态')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('db_name', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sqlmanager.DBModel', verbose_name='数据库名')),
                ('exec_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='执行人')),
                ('sql_workform', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='workform.WorkFormModel', verbose_name='关联的工单')),
            ],
            options={
                'verbose_name': 'SQL记录表',
                'db_table': 'sqldetail',
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='SQLExecDetailModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sql', models.CharField(max_length=5000, verbose_name='单条sql语句')),
                ('sql_tablename', models.CharField(max_length=50, null=True, verbose_name='sql表名')),
                ('exec_result', models.CharField(choices=[('success', '成功'), ('failed', '失败'), ('noneed', '不需要'), ('noexec', '未执行')], default='noexec', max_length=10, verbose_name='sql执行结果')),
                ('backup_result', models.CharField(choices=[('success', '成功'), ('failed', '失败'), ('noneed', '不需要'), ('noexec', '未执行')], max_length=10, null=True, verbose_name='sql备份结果')),
                ('check_affected_rows', models.CharField(max_length=100, null=True, verbose_name='sql检查影响的行数')),
                ('affected_rows', models.CharField(max_length=100, null=True, verbose_name='sql执行影响的行数')),
                ('errormessage', models.CharField(max_length=500, null=True, verbose_name='sql执行错误信息')),
                ('backup_dbname', models.CharField(max_length=100, null=True, verbose_name='备份的库名')),
                ('execute_time', models.CharField(max_length=50, null=True, verbose_name='sql执行时间')),
                ('seqnum', models.CharField(max_length=100, null=True, verbose_name='sql执行序列号')),
                ('sql_sha1', models.CharField(max_length=100, null=True, verbose_name='sql的sha1')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('last_update_time', models.DateTimeField(auto_now=True, verbose_name='最近修改时间')),
                ('sql_block', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sqlmanager.SQLDetailModel', verbose_name='关联的sql块或文件')),
            ],
            options={
                'verbose_name': 'SQL执行结果表',
                'db_table': 'sqlexec_detail',
                'ordering': ['id'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='dbclustermodel',
            unique_together=set([('name', 'env')]),
        ),
        migrations.AlterUniqueTogether(
            name='dbinstancemodel',
            unique_together=set([('name', 'env')]),
        ),
    ]