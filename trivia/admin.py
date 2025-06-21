from django.contrib import admin
from .models import  DailyTriviaSet, TriviaSession, TriviaQuestion, TriviaProfile

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
    
@admin.register(TriviaProfile)
class TriviaProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "last_played", "coins_earned", "total_quizzes_played", "total_correct_answers", "referral_count", "seven_day_streak")
    search_fields = ("user__email",)
    list_filter = ("last_played",)
    readonly_fields = ("user", "created_at", "updated_at")
    fieldsets = (
        (None, {
            'fields': ('user', 'last_played', 'coins_earned', 'total_quizzes_played', 'total_correct_answers', 'referral_count', 'seven_day_streak')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )