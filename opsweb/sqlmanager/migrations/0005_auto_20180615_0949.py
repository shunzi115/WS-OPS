# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-06-15 09:49
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sqlmanager', '0004_sqlrollbackmodel_rollback_exec_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sqlrollbackmodel',
            name='sql_already_exec',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sqlmanager.SQLExecDetailModel', verbose_name='关联已执行的SQL语句'),
        ),
    ]