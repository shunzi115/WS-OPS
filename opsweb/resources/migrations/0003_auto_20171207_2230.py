# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-12-07 22:30
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0002_auto_20171207_2151'),
    ]

    operations = [
        migrations.AlterField(
            model_name='server_aliyun',
            name='expired_time',
            field=models.DateTimeField(null=True, verbose_name='服务器过期时间'),
        ),
        migrations.AlterField(
            model_name='server_aliyun',
            name='last_update_time',
            field=models.DateTimeField(auto_now=True, null=True, verbose_name='最后一次更新时间'),
        ),
        migrations.AlterField(
            model_name='server_aliyun',
            name='offline_time',
            field=models.DateTimeField(null=True, verbose_name='服务器下架时间'),
        ),
        migrations.AlterField(
            model_name='server_aliyun',
            name='online_time',
            field=models.DateTimeField(auto_now_add=True, null=True, verbose_name='服务器上架时间'),
        ),
        migrations.AlterField(
            model_name='server_idc',
            name='last_update_time',
            field=models.DateTimeField(auto_now=True, null=True, verbose_name='最后一次更新时间'),
        ),
        migrations.AlterField(
            model_name='server_idc',
            name='online_time',
            field=models.DateTimeField(auto_now_add=True, null=True, verbose_name='服务器上架时间'),
        ),
    ]
