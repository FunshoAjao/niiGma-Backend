from django.contrib import admin
from .models import TriviaProfile, TriviaQuestion, TriviaAnswer, TriviaSession

@admin.register(TriviaProfile)
class TriviaProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'last_played', 'coins_earned', 'total_quizzes_played')

@admin.register(TriviaQuestion)
class TriviaQuestionAdmin(admin.ModelAdmin):
    list_display = ('question', 'correct_option')
    search_fields = ('question',)

@admin.register(TriviaAnswer)
class TriviaAnswerAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'selected_option', 'is_correct')
    list_filter = ('is_correct',)

@admin.register(TriviaSession)
class TriviaSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'score', 'coins_earned', 'completed')
    list_filter = ('completed',)