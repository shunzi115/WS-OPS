# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-06-23 19:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sqlmanager', '0009_auto_20180619_1603'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sqlchecktmpmodel',
            name='sql_detail',
            field=models.CharField(max_length=20000, verbose_name='sql语句'),
        ),
    ]
