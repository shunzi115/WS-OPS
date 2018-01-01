# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-01-01 16:03
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='servermodel',
            name='disk',
            field=models.CharField(max_length=300, null=True, verbose_name='物理磁盘大小'),
        ),
        migrations.AlterField(
            model_name='servermodel',
            name='disk_mount',
            field=models.CharField(max_length=500, null=True, verbose_name='分区挂载情况'),
        ),
    ]