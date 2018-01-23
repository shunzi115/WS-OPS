# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-01-23 02:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workform', '0014_auto_20180123_1004'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workformmodel',
            name='level',
            field=models.PositiveSmallIntegerField(choices=[(0, '重要且紧急'), (1, '不重要但紧急'), (2, '重要但不紧急'), (3, '不重要且不紧急')], max_length=5, verbose_name='紧急程度'),
        ),
    ]
