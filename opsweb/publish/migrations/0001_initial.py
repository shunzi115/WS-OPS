# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-04-20 11:46
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('resources', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PublishHistoryModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('success', '成功'), ('failure', '失败')], max_length=10, null=True, verbose_name='发布状态')),
                ('env', models.CharField(choices=[('online', '生产'), ('gray', '预发布')], max_length=10, null=True, verbose_name='环境')),
                ('type', models.CharField(choices=[('publish', '发布'), ('rollback', '回滚')], max_length=10, null=True, verbose_name='类型')),
                ('pub_time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='发布时间')),
                ('pub_log_file', models.CharField(max_length=200, null=True, verbose_name='发布脚本执行日志')),
                ('ip', models.ManyToManyField(to='resources.ServerModel', verbose_name='模块的服务器IP地址')),
                ('module_name', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='resources.CmdbModel', verbose_name='模块名')),
                ('pub_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='发布人')),
            ],
            options={
                'verbose_name': '发布历史表',
                'db_table': 'publish_history',
                'ordering': ['-id'],
            },
        ),
        migrations.CreateModel(
            name='PublishVersionModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.CharField(max_length=100, unique=True, verbose_name='版本号')),
                ('status', models.CharField(choices=[('running', '当前运行的主版本'), ('run_pre', '之前运行过的版本'), ('rollback', '发生了回滚的版本'), ('packed', '已经打包且未发布的版本')], default='packed', max_length=10, verbose_name='版本状态')),
                ('pack_time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='打包时间')),
                ('jenkins_url', models.URLField(max_length=100, null=True, verbose_name='jenkins 地址')),
                ('pack_user', models.CharField(max_length=50, null=True, verbose_name='打包人')),
                ('module_name', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='resources.CmdbModel', verbose_name='模块名')),
            ],
            options={
                'verbose_name': '版本记录表',
                'db_table': 'publish_version',
                'ordering': ['-id'],
            },
        ),
        migrations.AddField(
            model_name='publishhistorymodel',
            name='version_now',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='publish.PublishVersionModel', verbose_name='当前发布的版本号'),
        ),
    ]
