import os
from celery import Celery
from django.conf import settings
from celery.schedules import crontab

print("🚀 Initializing Celery")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("core")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.broker_connection_retry_on_startup = True
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'send-reminders-every-minute': {
        'task': 'reminders.services.tasks.send_due_reminders',
        'schedule': crontab(minute='*'),  # every minute
    },
}

print("✅ Celery configured")