import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "witswin.settings")

app = Celery("witswin")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()



# app.conf.event_serializer = 'pickle'
# app.conf.task_serializer = 'pickle'
# app.conf.result_serializer = 'pickle'
# app.conf.accept_content = ['application/json', 'application/x-python-serialize']

