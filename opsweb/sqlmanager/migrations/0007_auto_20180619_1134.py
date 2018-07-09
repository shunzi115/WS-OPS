# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-06-19 11:34
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sqlmanager', '0006_inceptionbackgroundmodel'),
    ]

    operations = [
        migrations.CreateModel(
            name='InceptionDangerSQLModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sql_keyword', models.CharField(max_length=5000, verbose_name='高危SQL关键字')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('last_update_time', models.DateTimeField(auto_now=True, verbose_name='最近修改时间')),
            ],
            options={
                'verbose_name': 'Inception 自定义高危SQL',
                'db_table': 'inception_danger_sql',
                'ordering': ['id'],
            },
        ),
        migrations.AddField(
            model_name='inceptionbackgroundmodel',
            name='inc_backup_password',
            field=models.CharField(max_length=100, null=True, verbose_name='Inception 备份服务器密码'),
        ),
        migrations.AlterField(
            model_name='inceptionbackgroundmodel',
            name='inc_backup_username',
            field=models.CharField(max_length=50, null=True, verbose_name='Inception 备份服务器账号'),
        ),
    ]