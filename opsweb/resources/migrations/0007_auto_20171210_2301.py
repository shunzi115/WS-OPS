# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-12-10 15:01
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0006_auto_20171210_2218'),
    ]

    operations = [
        migrations.AddField(
            model_name='server_aliyun',
            name='instance_id',
            field=models.CharField(db_index=True, max_length=50, null=True, unique=True, verbose_name='实例ID'),
        ),
        migrations.AlterField(
            model_name='server_aliyun',
            name='private_ip',
            field=models.GenericIPAddressField(db_index=True, null=True, protocol='IPv4', unique=True, verbose_name='私网IP'),
        ),
    ]
