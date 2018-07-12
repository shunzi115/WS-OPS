from sqlmanager.models import SQLExecDetailModel
from django.db.models import F,Q
from django.db.models import Count
from datetime import *

time_interval = timedelta(days=30)
seven_days_ago = date.today() - time_interval

def get_db_type_count():

    charts_data = {"name":"数据库更新 TOP10","children":[]}

    my_queryset = SQLExecDetailModel.objects.filter(create_time__gt=seven_days_ago).filter(exec_result__exact='success').annotate(db_name=F("sql_block__db_name__name")).values("sql_type","db_name")

    ''' [{'db_name': 'mytest', 'db_count': 96}, {'db_name': 'zabbix', 'db_count': 28}] '''
    db_opera_top10 = list(my_queryset.values("db_name").annotate(db_count=Count("id")).order_by("-db_count"))[:10]
    db_name_str = '|'.join(['Q(db_name__exact="%s")' %(db["db_name"]) for db in db_opera_top10 ])

    ''' [{'sql_type': 'UPDATE', 'db_name': 'zabbix', 'type_count': 1},{'sql_type': 'ALTERTABLE', 'db_name': 'mytest', 'type_count': 1}] '''

    db_type_list = list(my_queryset.annotate(type_count=Count("id")).filter(eval(db_name_str)).order_by("db_name","-type_count")) if db_name_str else []

    for dbs in db_opera_top10:
        db_data = {}
        db_data["name"] = dbs.get("db_name")
        db_data["children"] = [ {"name":dt.get("sql_type"),"value":dt.get("type_count")} for dt in db_type_list if dt["db_name"] == dbs.get("db_name") and dt.get("sql_type") ]
        charts_data["children"].append(db_data)

    return charts_data



