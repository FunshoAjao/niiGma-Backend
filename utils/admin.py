from django.contrib import admin
from .models import DailyWindDownQuote, UserAIInsight

@admin.register(DailyWindDownQuote)
class DailyWindDownQuoteAdmin(admin.ModelAdmin):
    list_display = ("date",)

@admin.register(UserAIInsight)
class UserAIInsightAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "insight_type")
    search_fields = ("user__email", "context_tag", "insight_type")
    list_filter = ("insight_type", "date")
    ordering = ("-date",)
    list_per_page = 20
    date_hierarchy = "date"