from celery import shared_task
from django.utils import timezone
import logging
from django.utils.timezone import now
from calories.choices import ReminderChoices
from calories.models import LoggedMeal
from utils.helpers.fcm import PushNotificationService
logger = logging.getLogger(__name__)
from accounts.models import User
from ..models import Reminder
from django.db.models import Q

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
    
    if not logs.exists():
        return {
            "average_calories": 0,
            "under_target": None,
            "message": "No meals logged this week. Try logging your meals daily."
        }

    total = sum(log.calories for log in logs)
    avg_per_day = total / 7
    
    if not hasattr(user, "calorie_qa") or not user.calorie_qa.daily_calorie_target:
        return {
            "average_calories": avg_per_day,
            "under_target": None,
            "message": "No calorie target set. Please update your calorie profile."
        }
        
    under_target = avg_per_day < user.calorie_qa.daily_calorie_target  

    return {
        "average_calories": avg_per_day,
        "under_target": under_target,
        "message": f"You’re {'under' if under_target else 'on/over'} your target this week.",
    }

def send_push_notification(title, message, device_type, registration_token):
    print('About to send reminder now')
    PushNotificationService(device_type=device_type).send_push_notification(title=title, body=message, registration_token=registration_token)

@shared_task
def trigger_user_daily_meal_reminders():
    now = timezone.now()
    logger.info(f"About to trigger_user_daily_meal_reminders @ {now.date} ")
    Reminder().send_daily_meal_reminders()
    
@shared_task
def trigger_send_reminders_if_user_forgot_to_log_meal():
    now = timezone.now()
    logger.info(f"About to trigger_send_reminders_if_user_forgot_to_log_meal @ {now.date} ")
    Reminder().send_reminders_if_user_forgot_to_log_meal()
    
@shared_task
def trigger_weekly_insights_for_all_users():
    now = timezone.now()
    logger.info(f"About to trigger_weekly_insights_for_all_users @ {now.date} ")
    Reminder().generate_weekly_insights_for_all_users()

class Reminder:
    def __init__(self, user: User=None):
        self.user = user
        
    def generate_weekly_insights_for_all_users(self):
        from datetime import timedelta

        users = User.objects.filter(is_active=True, calorie_qa__isnull=False, allow_push_notifications=True)

        now = timezone.now()
        week_ago = now - timedelta(days=7)

        for user in users:
            logs = LoggedMeal.objects.filter(user=user, date__gte=week_ago)

            if not logs.exists():
                insight = "No meals logged this week. Try logging your meals daily for better insights."
                average = total = 0
            else:
                total = sum(log.calories for log in logs)
                average = total / 7

                if not hasattr(user, "calorie_qa") or not user.calorie_qa.daily_calorie_target:
                    insight = f"You logged meals but no target is set. Your average intake is {round(average)} cal/day."
                else:
                    target = user.calorie_qa.daily_calorie_target
                    if average < target:
                        insight = f"Great job! You stayed under your target. Avg: {round(average)} cal/day (target: {target})."
                    else:
                        insight = f"You went over your target this week. Avg: {round(average)} cal/day (target: {target}). Let's improve next week!"
        
            # Optional: Notify user
            send_push_notification(
                title="Your Weekly Wellness Insight 🧠",
                message=insight,
                device_type=user.device_type,
                registration_token = user.device_token
            )

        
    def trigger_reminders_for_user_to_log_meal(self):
        today = now().date()
        users = User.objects.filter(
            is_active=True,
            calorie_qa__isnull=False,
            allow_push_notifications=True
        ).select_related("calorie_qa")

        title = "Calorie Reminder"
        daily_msg = "Time to log your meal on the Niigma app today!"
        forget_msg = "It's not too late! Log your meal on the Niigma app now."

        for user in users:
            reminder_type = user.calorie_qa.reminder
            device_type = user.device_type
            device_token = user.device_token
            
            if reminder_type == ReminderChoices.Daily or reminder_type == str(ReminderChoices.Daily).capitalize():
                send_push_notification(title, daily_msg, device_type, device_token)
            elif reminder_type == ReminderChoices.Only_If_I_Forget:
                has_logged_today = LoggedMeal.objects.filter(
                    user=user,
                    date__date=today
                ).exists()
                if not has_logged_today:
                    send_push_notification(title, forget_msg, device_type, device_token)
                
    def send_daily_meal_reminders(self):
        users = User.objects.filter(
            is_active=True,
            calorie_qa__isnull=False,
            allow_push_notifications=True
        ).filter(
            Q(calorie_qa__reminder=ReminderChoices.Daily) |
            Q(calorie_qa__reminder=ReminderChoices.Daily.capitalize())
        ).select_related("calorie_qa")

        title = "Calorie Reminder"
        message = "Time to log your meal on the Niigma app today!"
        
        for user in users:
            send_push_notification(title, message, user.device_type, user.device_token)
            
    def send_reminders_if_user_forgot_to_log_meal(self):
        today = now().date()

        users = User.objects.filter(
            is_active=True,
            calorie_qa__isnull=False,
            allow_push_notifications=True
        ).filter(
            Q(calorie_qa__reminder=ReminderChoices.Only_If_I_Forget) |
            Q(calorie_qa__reminder=ReminderChoices.Only_If_I_Forget.capitalize())
        ).select_related("calorie_qa")

        title = "Calorie Reminder"
        message = "It's not too late! Log your meal on the Niigma app now."

        for user in users:
            has_logged_today = LoggedMeal.objects.filter(
                user=user,
                date__date=today
            ).exists()

            if not has_logged_today:
                send_push_notification(title, message, user.device_type, user.device_token)