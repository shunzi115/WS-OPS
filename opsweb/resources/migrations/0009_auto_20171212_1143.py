# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-12-12 03:43
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0008_auto_20171210_2314'),
    ]

    operations = [
        migrations.AlterField(
            model_name='idc',
            name='name',
            field=models.CharField(max_length=20, unique=True, verbose_name='IDC 简称'),
        ),
    ]