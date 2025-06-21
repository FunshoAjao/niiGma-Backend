from django.contrib import admin
from .models import Reminder

@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'time', 'enabled')
    list_filter = ('type', 'enabled')
    search_fields = ('user__email', 'message')
    ordering = ('-time',)