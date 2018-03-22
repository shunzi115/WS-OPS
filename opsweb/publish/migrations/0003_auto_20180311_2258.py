# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-03-11 22:58
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('publish', '0002_auto_20180311_2129'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='publishhistorymodel',
            name='pub_status',
        ),
        migrations.AddField(
            model_name='publishhistorymodel',
            name='status',
            field=models.CharField(choices=[('success', '成功'), ('failure', '失败')], max_length=10, null=True, verbose_name='发布状态'),
        ),
        migrations.AddField(
            model_name='publishhistorymodel',
            name='type',
            field=models.CharField(choices=[('publish', '发布'), ('rollback', '回滚')], max_length=10, null=True, verbose_name='类型'),
        ),
    ]