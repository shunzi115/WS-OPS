# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-06-26 10:04
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sqlmanager', '0013_sqldetailmodel_applicant_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sqldetailmodel',
            name='applicant_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sql_applicant_user', to=settings.AUTH_USER_MODEL, verbose_name='申请人'),
        ),
    ]