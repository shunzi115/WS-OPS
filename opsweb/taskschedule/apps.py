from django.apps import AppConfig

class TaskScheduleConfig(AppConfig):
    name = 'taskschedule'
    def ready(self):
        from taskschedule import signals
