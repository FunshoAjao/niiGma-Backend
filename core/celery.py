import os
from celery import Celery
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("core")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.broker_connection_retry_on_startup = True
app.autodiscover_tasks()

app.conf.update(
    broker_connection_retry_on_startup=True,
    broker_url=settings.BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,
)