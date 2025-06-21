from django.contrib import admin
from .models import  DailyTriviaSet, TriviaSession, TriviaQuestion

@admin.register(DailyTriviaSet)
class DailyQuestionAdmin(admin.ModelAdmin):
    list_display = ("date", "created_at")

@admin.register(TriviaSession)
class TriviaSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "started_at", "is_completed", "score", "source")
    list_filter = ("source", "is_completed")

@admin.register(TriviaQuestion)
class TriviaQuestionAdmin(admin.ModelAdmin):
    list_display = ("session", "question_text", "user_answer", "is_correct")
    search_fields = ("question_text",)