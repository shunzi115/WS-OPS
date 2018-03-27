from __future__ import absolute_import
import os
import django
from celery import Celery, platforms
from django.conf import settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'opsweb.settings')
django.setup()
app = Celery('opsweb')
platforms.C_FORCE_ROOT = True
app.config_from_object('django.conf:settings')
