from django.contrib import admin
from .models import DailyWindDownQuote

@admin.register(DailyWindDownQuote)
class DailyWindDownQuoteAdmin(admin.ModelAdmin):
    list_display = ("date",)
