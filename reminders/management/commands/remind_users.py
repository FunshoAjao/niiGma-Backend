from django.core.management.base import BaseCommand

from ...services import tasks

class Command(BaseCommand):
    help = "Send calorie reminder notifications"

    def handle(self, *args, **kwargs):
        tasks.Reminder().generate_weekly_insights_for_all_users()
        tasks.Reminder().trigger_reminders_for_user_to_log_meal()
        tasks.Reminder().send_daily_meal_reminders()
        tasks.Reminder().send_reminders_if_user_forgot_to_log_meal()
        self.stdout.write("Reminders sent.")
