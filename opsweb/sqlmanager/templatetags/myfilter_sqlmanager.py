from django import template
from django.contrib.auth.models import Group

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
