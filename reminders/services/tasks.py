from celery import shared_task
from django.utils import timezone
import logging

from utils.helpers.fcm import PushNotificationService
logger = logging.getLogger(__name__)
from accounts.models import User
from ..models import Reminder

@shared_task
def send_due_reminders():
    now = timezone.now().time()
    reminders = Reminder.objects.filter(time=now, enabled=True)
    if reminders.count() == 0:
        logger.info("No reminders due at this time.")
        return
    for reminder in reminders:
        # Trigger push/email/notification
        logger.info(f"Send reminder to {reminder.user.email}: {reminder.message}")

@shared_task
def generate_weekly_insights(user_id):
    from datetime import timedelta
    from django.utils import timezone
    from calories.models import LoggedMeal as MealLog

    user = User.objects.get(id=user_id)
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    logs = MealLog.objects.filter(user=user, time__gte=week_ago)

    total = sum(log.calories for log in logs)
    avg_per_day = total / 7
    under_target = avg_per_day < user.calorie_qa.daily_calorie_target  

    return {
        "average_calories": avg_per_day,
        "under_target": under_target,
        "message": f"You’re {'under' if under_target else 'on/over'} your target this week.",
    }

def send_push_notification(title, message, device_type, registration_token):
    PushNotificationService(device_type=device_type).send_push_notification(title=title, body=message, registration_token=registration_token)
