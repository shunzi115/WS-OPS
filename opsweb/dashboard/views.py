from django.shortcuts import render,reverse
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from  api.myapi.get_workform_info import GetWorkFormInfo


class IndexView(LoginRequiredMixin,TemplateView):
    template_name = "index.html"
    wf_info = GetWorkFormInfo()

    def get_context_data(self):
        context = super(IndexView,self).get_context_data()
        context["workform_count_today"] = self.wf_info.get_workform_today_count()
        context["workform_type_echart_data"] = self.wf_info.get_workform_count_by_type()
        context["workform_reason_echart_data"] = self.wf_info.get_workform_count_by_reason()
        context["workform_module_echart_data"] = self.wf_info.get_workform_count_by_module()
        return context

class NoPermissionView(TemplateView):
    template_name = "public/no_permission.html"

    def get_context_data(self,**kwargs):
        context = super(NoPermissionView, self).get_context_data(**kwargs)
        uri_name = self.kwargs.get("next_uri", "index")
        try:
            next_uri = reverse(uri_name)
        except:
            pass
        context['next_uri'] = next_uri
        return context
