from django.conf.urls import include, url
from django.contrib import admin
from . import views,api,inception_relate
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    url(r'^mysql/db/',include([
        url(r'^list/$',views.DBListView.as_view(),name="mysql_list"),
        url(r'^add/$',views.DBAddView.as_view(),name="mysql_add"),
        url(r'^change/$',views.DBChangeView.as_view(),name="mysql_change"),
        url(r'^delete/$',views.DBDeleteView.as_view(),name="mysql_delete"),
    ])),

    url(r'^mysql/cluster/',include([
        url(r'^list/$',views.DBClusterListView.as_view(),name="mysql_cluster_list"),
        url(r'^add/$',views.DBClusterAddView.as_view(),name="mysql_cluster_add"),
        url(r'^change/$',views.DBClusterChangeView.as_view(),name="mysql_cluster_change"),
        url(r'^delete/$',views.DBClusterDeleteView.as_view(),name="mysql_cluster_delete"),
        url(r'^relate/',views.DBClusterRelateView.as_view(),name="mysql_cluster_relate"),
    ])),

    url(r'^mysql/instance/',include([
        url(r'^list/$',views.DBInstanceListView.as_view(),name="mysql_instance_list"),
        url(r'^add/$',views.DBInstanceAddView.as_view(),name="mysql_instance_add"),
        url(r'^info/$',views.DBInstanceMoreInfoView.as_view(),name="mysql_instance_more_info"),
        url(r'^change/$',views.DBInstanceChangeView.as_view(),name="mysql_instance_change"),
        url(r'^delete/$',views.DBInstanceDeleteView.as_view(),name="mysql_instance_delete"),
    ])),

    url(r'^sql/',include([
        url(r'^check/$',inception_relate.InceptionSqlCheckView.as_view(),name="inception_sql_check"),
        url(r'^check/result/$',inception_relate.InceptionSqlCheckResultView.as_view(),name="inception_sql_check_result"),
        url(r'^split/result/$',inception_relate.InceptionSqlSplitResultView.as_view(),name="inception_sql_split_result"),
        url(r'^add/$',inception_relate.InceptionSqlAddView.as_view(),name="inception_sql_add"),
        url(r'^noexec/list/$',inception_relate.InceptionSqlNoexecView.as_view(),name="inception_sql_noexec_list"),
        url(r'^history/list/$',inception_relate.InceptionSqlHistoryView.as_view(),name="inception_sql_history_list"),
        url(r'^pause/$',inception_relate.InceptionSqlPauseView.as_view(),name="inception_sql_pause"),
        url(r'^refuse/$',inception_relate.InceptionSqlRefuseView.as_view(),name="inception_sql_refuse"),
        url(r'^exec/$',inception_relate.InceptionSqlExecView.as_view(),name="inception_sql_exec"),
        url(r'^exec/result/$',inception_relate.InceptionSqlExecResultView.as_view(),name="inception_sql_exec_result"),
        url(r'^rollback/$',inception_relate.InceptionSqlRollBackupView.as_view(),name="inception_sql_rollback"),
        url(r'^rollback/result/$',inception_relate.InceptionSqlRollbackResultView.as_view(),name="inception_sql_rollback_result"),
        url(r'^stop/osc/$',inception_relate.InceptionStopOscView.as_view(),name="inception_stop_osc"),
        url(r'^ops/commit/$',inception_relate.InceptionDbaCommitView.as_view(),name="inception_ops_dba_commit"),

    ])),

    url(r'^background/',include([
        url(r'^list/$',inception_relate.InceptionBackgroundManageView.as_view(),name="inc_background_manage"),
        url(r'^change/$',inception_relate.InceptionBackgroundManageChangeView.as_view(),name="inc_background_manage_change"),
    ])),

    url(r'^danger/sql',include([
        url(r'^add/$',inception_relate.InceptionDangerSQLAddView.as_view(),name="inception_danger_sql_add"),
        url(r'^change/$',inception_relate.InceptionDangerSQLChangeView.as_view(),name="inception_danger_sql_change"),
        url(r'^delete/$',inception_relate.InceptionDangerSQLDeleteView.as_view(),name="inception_danger_sql_delete"),
    ])),
]
