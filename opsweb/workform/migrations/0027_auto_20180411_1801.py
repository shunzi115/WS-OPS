# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-04-11 18:01
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workform', '0026_workformmodel_database_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workformmodel',
            name='database_name',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='数据库名称'),
        ),
    ]