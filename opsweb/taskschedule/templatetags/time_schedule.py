from django import template
from django.db.models import Q

register = template.Library()

@register.filter(name="get_crontab_schedule")
def get_crontab_schedule(value):
    return "%s %s %s %s %s" %(value.minute,value.hour,value.day_of_month,value.month_of_year,value.day_of_week)

@register.filter(name="get_interval_schedule")
def get_interval_schedule(value):
    return "%s %s" %(value.every,value.period)

