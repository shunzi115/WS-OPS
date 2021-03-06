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
from . import views
from django.views.decorators.cache import cache_page

urlpatterns = [
    url(r'^$', views.IndexView.as_view(),name="index"),
    url(r'^portal/$',views.InnerPortalView.as_view(),name="inner_portal"),
    url(r'^nopermission/(?P<next_uri>[\s\S]*)/$', views.NoPermissionView.as_view(),name="no_permission"),
    url(r'^justfortest/$',cache_page(20)(views.JustForTestRedis.as_view()),name="justfortest"),
    # url(r'^justfortest/$',views.JustForTestRedis.as_view(),name="justfortest"),
]
