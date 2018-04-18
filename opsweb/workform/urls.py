
from django.conf.urls import include, url
from django.contrib import admin
from . import views,workform_type,workform_process
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    url(r'^pub/',include([
        url(r'^add/$',views.PubWorkFormAddView.as_view(),name="pub_workform_add"),
        url(r'^detail/(?P<pk>\d+)/$',views.WorkFormDetailView.as_view(),name="pub_workform_detail"),
    ])),

    url(r'^sql/',include([
        url(r'^add/$',views.SqlWorkFormAddView.as_view(),name="sql_workform_add"),
    ])),

    url(r'^others/',include([
        url(r'^add/$',views.OthersWorkFormAddView.as_view(),name="others_workform_add"),
    ])),

    url(r'^add/$',views.WorkFormAddBaseView.as_view(),name="workform_add"),
    url(r'^list/$',views.WorkFormListView.as_view(),name="workform_list"),
    url(r'^delete/$',views.WorkFormDeleteView.as_view(),name="workform_delete"),

    url(r'^process/',include([
        url(r'^trace/$',views.ProcessTraceView.as_view(),name="process_trace"),
        url(r'^step/approval$',views.ProcessStepApprovalInfoView.as_view(),name="process_step_approval"),
    ])),

    url(r'^my/',include([
        url(r'^list/$',views.MyWorkFormListView.as_view(),name="my_workform_list"),
        url(r'^approval/$',views.ApprovalWorkFormView.as_view(),name="workform_approval"),
    ])),

    url(r'^info/$',views.WorkFormInfoView.as_view(),name="workform_info"),

    url(r'^upload/',include([
        url(r'^$',views.WorkFormUploadView.as_view(),name="workform_upload"),
        url(r'^(?P<filename>[\s\S]*)/$',views.WorkFormUploadFilePreviewView.as_view(),name="workform_upload_file_preview"),
    ])),

    url(r'^type/',include([
        url(r'^list/$',workform_type.WorkFormTypeListView.as_view(),name="workform_type_list"),
        url(r'^add/$',workform_type.WorkFormTypeAddView.as_view(),name="workform_type_add"),
        url(r'^delete/$',workform_type.WorkFormTypeDeleteView.as_view(),name="workform_type_delete"),
        url(r'^change/$',workform_type.WorkFormTypeChangeView.as_view(),name="workform_type_change"),
    ])),

    url(r'^process/',include([
        url(r'^list/$',workform_process.WorkFormProcessListView.as_view(),name="workform_process_list"),
        url(r'^add/$',workform_process.WorkFormProcessAddView.as_view(),name="workform_process_add"),
        url(r'^delete/$',workform_process.WorkFormProcessDeleteView.as_view(),name="workform_process_delete"),
        url(r'^change/$',workform_process.WorkFormProcessChangeView.as_view(),name="workform_process_change"),
    ])),
]
