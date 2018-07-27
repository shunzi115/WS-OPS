from django import template

register = template.Library()

@register.filter(name="replace_to_br")
def replace_to_br(value,args):
    if args and args in value:
        return value.replace(args,'<br>')
    else:
        return value

@register.filter(name="get_version")
def get_version(value):
    version_list = []
    ip_ibj_list = value.ips.all().distinct()
    for ip_obj in ip_ibj_list:
        try:
            ph_obj = ip_obj.publishhistorymodel_set.filter(module_name__exact=value).latest("id")
        except Exception as e:
            pass
        else:
            version_list.append(ph_obj.version_now.version)
    if not version_list:
        return None
    else:
        return '<br>'.join(list(set(version_list)))
