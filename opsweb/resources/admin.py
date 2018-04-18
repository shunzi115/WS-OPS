from django.contrib import admin
from .models import ServerModel
# Register your models here.
admin.site.empty_value_display = '(None)'

admin.site.register(ServerModel)
