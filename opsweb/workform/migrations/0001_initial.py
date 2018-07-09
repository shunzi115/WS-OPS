# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-05-23 22:29
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
            name='ApprovalFormModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('result', models.CharField(choices=[('0', '审批/验证通过'), ('1', '拒绝审批/执行'), ('2', '暂停审批/执行'), ('3', '执行/验证异常')], max_length=10, null=True, verbose_name='审批/执行结果')),
                ('approve_note', models.CharField(max_length=1000, null=True, verbose_name='审批/执行备注')),
                ('approval_time', models.DateTimeField(null=True, verbose_name='审批时间')),
                ('approver', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='最终审批/执行人')),
                ('approver_can', models.ManyToManyField(null=True, related_name='_approvalformmodel_approver_can_+', to=settings.AUTH_USER_MODEL, verbose_name='实际能审批/执行的用户集合')),
            ],
            options={
                'verbose_name': '审批表',
                'db_table': 'approval_form',
                'ordering': ['-id'],
            },
        ),
        migrations.CreateModel(
            name='ProcessModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('step', models.CharField(max_length=50, unique=True, verbose_name='流程步骤')),
                ('step_id', models.PositiveSmallIntegerField(unique=True, verbose_name='步骤id')),
                ('approval_require', models.CharField(choices=[('0', '终级大boss'), ('1', '用户所属组leader'), ('2', 'QA组'), ('3', 'OPS组'), ('4', '用户自己'), ('5', '指定具体某个用户'), ('6', '雪良组'), ('7', '君禄组'), ('8', '华俊组'), ('9', '无')], max_length=10, verbose_name='期待有审核权限的用户或组,只是一个标记,具体逻辑后端定义')),
            ],
            options={
                'verbose_name': '工单流程表',
                'db_table': 'process',
                'ordering': ['step_id'],
            },
        ),
        migrations.CreateModel(
            name='WorkFormModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100, unique=True, verbose_name='工单标题')),
                ('level', models.PositiveSmallIntegerField(choices=[(0, '重要且紧急'), (1, '不重要但紧急'), (2, '重要但不紧急'), (3, '不重要且不紧急')], verbose_name='紧急程度')),
                ('reason', models.CharField(choices=[('0', '项目需求'), ('1', '故障修复'), ('2', '技术优化'), ('3', '其他')], max_length=10, null=True, verbose_name='上线原因')),
                ('detail', models.CharField(max_length=800, null=True, verbose_name='详情')),
                ('status', models.CharField(choices=[('0', '待审批'), ('1', '审批中'), ('2', '已完成'), ('3', '暂停'), ('4', '取消')], default='0', max_length=10, verbose_name='工单状态')),
                ('create_time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='工单创建时间')),
                ('complete_time', models.DateTimeField(null=True, verbose_name='工单完成时间')),
                ('module_name', models.CharField(max_length=500, null=True, verbose_name='模块名称')),
                ('sql', models.CharField(choices=[('yes', '有'), ('no', '无')], default='no', max_length=10, verbose_name='是否存在SQL')),
                ('applicant', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='申请人,与用户表多对一关联')),
                ('approver_can', models.ManyToManyField(related_name='_workformmodel_approver_can_+', to=settings.AUTH_USER_MODEL, verbose_name='与User表建立多对多关联,声明该流程步骤能审批/执行的用户集合,具体的用户集合从ApprovalFormModel的approver_can字段同步')),
                ('process_step', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='workform.ProcessModel', verbose_name='与流程步骤多对一关联')),
            ],
            options={
                'verbose_name': '工单列表',
                'db_table': 'workform',
                'ordering': ['-id'],
            },
        ),
        migrations.CreateModel(
            name='WorkFormTypeModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='工单类型名称')),
                ('cn_name', models.CharField(max_length=200, unique=True, verbose_name='工单类型中文名称')),
                ('process_step_id', models.CharField(max_length=500, null=True, verbose_name='需要执行的工单流程')),
            ],
            options={
                'verbose_name': '工单类型表',
                'db_table': 'workform_type',
            },
        ),
        migrations.AddField(
            model_name='workformmodel',
            name='type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='workform.WorkFormTypeModel', verbose_name='工单类型,与工单类型表多对一关联'),
        ),
        migrations.AddField(
            model_name='approvalformmodel',
            name='process',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='workform.ProcessModel', verbose_name='与发布流程步骤多对一关联'),
        ),
        migrations.AddField(
            model_name='approvalformmodel',
            name='workform',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='workform.WorkFormModel', verbose_name='关联发布工单记录'),
        ),
        migrations.AlterIndexTogether(
            name='approvalformmodel',
            index_together=set([('process', 'workform')]),
        ),
    ]