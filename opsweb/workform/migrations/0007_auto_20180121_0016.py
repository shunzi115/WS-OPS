# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-01-20 16:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workform', '0006_remove_processmodel_applicant_require_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='approvalformmodel',
            name='approval_time',
            field=models.DateTimeField(null=True, verbose_name='审批时间'),
        ),
    ]
