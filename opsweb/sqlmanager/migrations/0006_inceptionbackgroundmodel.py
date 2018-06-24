# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-06-19 10:39
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sqlmanager', '0005_auto_20180615_0949'),
    ]

    operations = [
        migrations.CreateModel(
            name='InceptionBackgroundModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('inc_ip', models.GenericIPAddressField(protocol='IPv4', verbose_name='Inception 服务器IP')),
                ('inc_port', models.CharField(max_length=5, verbose_name='Inception 服务器端口')),
                ('inc_backup_ip', models.GenericIPAddressField(null=True, protocol='IPv4', verbose_name='Inception 备份服务器IP')),
                ('inc_backup_port', models.CharField(max_length=5, null=True, verbose_name='Inception 备份服务器端口')),
                ('inc_backup_username', models.CharField(max_length=100, null=True, verbose_name='Inception 备份服务器密码')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('last_update_time', models.DateTimeField(auto_now=True, verbose_name='最近修改时间')),
            ],
            options={
                'verbose_name': 'Inception 后台管理表',
                'db_table': 'inception_background_manage',
                'ordering': ['id'],
            },
        ),
    ]
