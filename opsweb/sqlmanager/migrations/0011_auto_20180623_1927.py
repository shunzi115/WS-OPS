# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-06-23 19:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sqlmanager', '0010_auto_20180623_1924'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sqldetailmodel',
            name='exec_status',
            field=models.CharField(choices=[('0', '执行成功'), ('1', '执行有错误'), ('2', '未执行')], default='2', max_length=10, verbose_name='执行状态'),
        ),
    ]