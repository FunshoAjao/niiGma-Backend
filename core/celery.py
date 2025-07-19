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
        "schedule": crontab(minute='*/50'),  # Runs every 50 minutes
    },
    'reset-calorie-streaks-daily': {
        'task': 'calories.services.tasks.reset_missed_calorie_streaks',
        'schedule': crontab(hour=3, minute=0),  # Every day at 3:00 AM
    },
    
    
    # for reminder
    "daily-user-meal-reminder": {
        "task": "reminders.services.tasks.trigger_user_daily_meal_reminders",
        "schedule": crontab(hour=9, minute=0),  # 9:00 AM every day
    },
    "periodic-user-meal-reminder": {
        "task": "reminders.services.tasks.trigger_send_reminders_if_user_forgot_to_log_meal",
        "schedule": crontab(minute=0, hour='17-21'),  # Every hour from 5 PM to 9 PM
    },
    "weekly-insights_reminder": {
        "task": "reminders.services.tasks.trigger_weekly_insights_for_all_users",
        "schedule": crontab(hour=10, minute=0, day_of_week='6'),  # Saturday (6) at 10:00 AM
    },
}

print("✅ Celery configured")