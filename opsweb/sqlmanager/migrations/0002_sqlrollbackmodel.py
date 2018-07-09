# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-06-13 00:18
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sqlmanager', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SQLRollBackModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sql_rollback', models.CharField(max_length=5000, null=True, verbose_name='sql的回滚语句')),
                ('rollback_check_affected_rows', models.CharField(max_length=100, null=True, verbose_name='sql检查影响的行数')),
                ('rollback_backup_dbname', models.CharField(max_length=100, null=True, verbose_name='备份的库名')),
                ('rollback_execute_time', models.CharField(max_length=50, null=True, verbose_name='sql执行时间')),
                ('rollback_seqnum', models.CharField(max_length=100, null=True, verbose_name='sql执行序列号')),
                ('sql_rollback_result', models.CharField(choices=[('success', '成功'), ('failed', '失败'), ('noneed', '不需要'), ('noexec', '未执行')], default='noexec', max_length=10, verbose_name='sql回滚结果')),
                ('rollback_affected_rows', models.CharField(max_length=100, null=True, verbose_name='sql执行回滚影响的行数')),
                ('rollback_errmsg', models.CharField(max_length=500, null=True, verbose_name='sql回滚错误信息')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('last_update_time', models.DateTimeField(auto_now=True, verbose_name='最近修改时间')),
                ('sql_already_exec', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='sqlmanager.SQLExecDetailModel', verbose_name='关联已执行的SQL语句')),
            ],
            options={
                'verbose_name': 'SQL回滚语句表',
                'db_table': 'sql_rollback',
                'ordering': ['id'],
            },
        ),
    ]