"""opsweb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic import RedirectView
from django.conf.urls.static import static  
from django.conf import settings  


urlpatterns = [
    url(r'^$', RedirectView.as_view(url="/dashboard/")),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/', include("accounts.urls")),
    url(r'^dashboard/', include("dashboard.urls")),
    url(r'^resources/', include("resources.urls")),
    url(r'^monitor/', include("monitor.urls")),
    url(r'^api/', include("api.urls")),
    url(r'^workform/', include("workform.urls")),
    url(r'^captcha/', include("captcha.urls")),
    url(r'^publish/', include("publish.urls")),
    url(r'^dbmanager/', include("dbmanager.urls")),
    url(r'^taskschedule/', include("taskschedule.urls")),
    url(r'^sqlmanager/', include("sqlmanager.urls")),
]
