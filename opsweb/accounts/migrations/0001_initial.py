# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-11-02 15:47
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserExtend',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cn_name', models.CharField(max_length=50, verbose_name='中文名')),
                ('phone', models.CharField(max_length=11, verbose_name='手机号')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='扩展用户表,与用户模型User建立一对一关系')),
            ],
            options={
                'db_table': 'user_extend',
            },
        ),
    ]
