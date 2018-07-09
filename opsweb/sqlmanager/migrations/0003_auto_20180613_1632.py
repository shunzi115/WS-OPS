# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-06-13 16:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sqlmanager', '0002_sqlrollbackmodel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sqldetailmodel',
            name='status',
            field=models.CharField(choices=[('0', '待执行'), ('1', '已执行'), ('2', '已回滚'), ('3', '暂停执行'), ('4', '拒绝执行'), ('5', '部分回滚')], default='0', max_length=10, verbose_name='状态'),
        ),
        migrations.AlterField(
            model_name='sqlexecdetailmodel',
            name='sql',
            field=models.CharField(max_length=10000, verbose_name='单条sql语句'),
        ),
        migrations.AlterField(
            model_name='sqlrollbackmodel',
            name='sql_rollback',
            field=models.CharField(max_length=10000, null=True, verbose_name='sql的回滚语句'),
        ),
    ]