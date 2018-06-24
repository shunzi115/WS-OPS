from django import template
from django.contrib.auth.models import Group
from api.thirdapi.inception_api import InceptionApi
import json

register = template.Library()

@register.filter(name="get_manager_group")
def get_manager_group(value):
    if not value.db_manage_group.all():
        return "None"

    manager_group_list = [i["name"] for i in value.db_manage_group.values("name")]
    return '<br>'.join(manager_group_list)

@register.filter(name="get_cluster")
def get_cluster(value):
    if not value.cluster_name.all():
        return "None"

    cluster_list = [i["name"] for i in value.cluster_name.values("name")]
    return '<br>'.join(cluster_list)
            
@register.filter(name="get_db_master_ip")
def get_master_ip(value):
    try:
        s_obj = value
        db_master_ip = s_obj.db_name.cluster_name.get(env__exact=s_obj.env).w_vip
    except:
        db_master_ip = ''

    return db_master_ip

@register.filter(name="get_osc_process")
def get_osc_process(value):
    s_exec_obj = value
    if not s_exec_obj.sql_sha1 or s_exec_obj.sql_block.sqlexecdetailmodel_set.filter(id__lt=s_exec_obj.id, exec_result__exact='noexec'):
        return 0
    inc_obj = InceptionApi("","","","",sql_str="")
    ret = inc_obj.inception_get_osc_process(s_exec_obj.sql_sha1)

    if ret["result"] == 1:
        return 0

    if ret["inc_result"]:
        inc_osc_result = ret["inc_result"][0]
        osc_percent = inc_osc_result[3]
        # osc_remain_time = inc_osc_result["REMAINTIME"]
        return osc_percent
    else:
        return 100

