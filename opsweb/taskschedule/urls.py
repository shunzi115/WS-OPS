from django.conf.urls import include, url
from django.contrib import admin
from . import views,api

urlpatterns = [
    url(r'^time/', include([
        url(r'^list/$',views.TimeScheduleListView.as_view(),name="time_schedule_list"),
    ])),
    url(r'^crontab/',include([
        url(r'^add/$',views.CrontabScheduleAddView.as_view(),name="crontab_schedule_add"),
        url(r'^update/$',views.CrontabScheduleUpdateView.as_view(),name="crontab_schedule_update"),
        url(r'^delete/$',views.CrontabScheduleDeleteView.as_view(),name="crontab_schedule_delete"),
    ])),
    url(r'^interval/',include([
        url(r'^add/$',views.IntervalScheduleAddView.as_view(),name="interval_schedule_add"),
        url(r'^update/$',views.IntervalScheduleUpdateView.as_view(),name="interval_schedule_update"),
        url(r'^delete/$',views.IntervalScheduleDeleteView.as_view(),name="interval_schedule_delete"),
    ])),
    url(r'^task/',include([
        url(r'^list/$',views.TaskListView.as_view(),name="task_list"),
        url(r'^add/$',views.TaskAddView.as_view(),name="task_add"),
        url(r'^delete/$',views.TaskDeleteView.as_view(),name="task_delete"),
        url(r'^update/$',views.TaskUpdateView.as_view(),name="task_update"),
        url(r'^info/$',views.TaskInfoView.as_view(),name="task_info"),
        url(r'^result/$',views.TaskResultListView.as_view(),name="task_result_list"),
        url(r'^result/delete/$',views.TaskResultDeleteView.as_view(),name="task_result_delete"),
    ])),
    url(r'^api/',include([
        url(r'^get/task/$',api.GetTaskView.as_view(),name="get_task_api"),
        url(r'^get/crontab/$',api.GetCrontabView.as_view(),name="get_crontab_api"),
        url(r'^get/interval/$',api.GetIntervalView.as_view(),name="get_interval_api"),
    ])),
]
