import os
from celery import Celery
from django.conf import settings
from celery.schedules import crontab
from datetime import timedelta

print("🚀 Initializing Celery")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("core")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.broker_connection_retry_on_startup = True
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'daily-trivia-sync-task': {
        'task': 'trivia.services.tasks.run_daily_question_sync',
        'schedule': crontab(minute=0),  # 00:00 every hour
    },
    'daily-wind-down-quote-task': {
        'task': 'mindspace.services.tasks.generate_daily_wind_down_quotes',
        'schedule': crontab(minute=5),  # 00:05 every hour
    },
    'weekly-mood-insight-task': {
        'task': 'mindspace.services.tasks.generate_weekly_user_insights',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    "daily-cycle-state-update": {
        "task": "ovulations.services.tasks.update_all_cycle_states",
        "schedule": crontab(minute='*/40'),  # Runs every 20 minutes
    },
}


print("✅ Celery configured")