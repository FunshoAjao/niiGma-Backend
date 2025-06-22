from django.db import models
from accounts.models import User
from calories.models import LoggedMeal
from common.models import BaseModel
from mindspace.models import MoodMirrorEntry
from django.utils import timezone
from datetime import date
from symptoms.models import SymptomSession
from trivia.choices import TriviaSessionTypeChoices

class TriviaProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="trivia_profile")
    last_played = models.DateField(null=True, blank=True)
    coins_earned = models.PositiveIntegerField(default=0)
    total_quizzes_played = models.PositiveIntegerField(default=0)
    total_correct_answers = models.PositiveIntegerField(default=0)
    referral_count = models.PositiveIntegerField(default=0)
    seven_day_streak = models.PositiveSmallIntegerField(default=0)  # count of consecutive days

    def __str__(self):
        return f"{self.user.email} - Trivia Profile"
    
    @property
    def has_logged_mood_today(self):
        return MoodMirrorEntry.objects.filter(
            mind_space__user=self.user,
            date__date=timezone.now().date()
        ).only("id").exists()

    @property
    def has_logged_calories_today(self):
        return LoggedMeal.objects.filter(
            user=self.user,
            created_at__date=timezone.now().date()
        ).only("id").exists()

    @property
    def has_used_symptom_checker_today(self):
        return SymptomSession.objects.filter(
            user=self.user,
            created_at__date=timezone.now().date()
        ).only("id").exists()

    @property
    def has_logged_ovulation_today(self):
        # return OvulationEntry.objects.filter(
        #     user=self.user,
        #     created_at__date=timezone.now().date()
        # ).only("id").exists()
        return True  # Placeholder for actual ovulation entry check

    @property
    def has_used_any_feature_today(self):
        return (
            self.has_logged_mood_today or
            self.has_logged_calories_today or
            self.has_used_symptom_checker_today or
            self.has_logged_ovulation_today
        )

class TriviaSession(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="trivia_sessions")
    started_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)
    source = models.CharField(max_length=20, choices=TriviaSessionTypeChoices.choices, default=TriviaSessionTypeChoices.Free)
    score = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.email} - {self.started_at.date()}"
    
    @property
    def completed(self):
        return self.questions.filter(user_answer__isnull=True).count() == 0

    @property
    def calculate_score(self):
        return self.questions.filter(is_correct=True).count()


class TriviaQuestion(BaseModel):
    session = models.ForeignKey(TriviaSession, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()
    choices = models.JSONField()
    correct_choice = models.CharField(max_length=5)
    explanation = models.TextField(blank=True)
    user_answer = models.CharField(max_length=1, null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return self.question_text
    

class DailyTriviaSet(BaseModel):
    date = models.DateField()
    questions = models.JSONField()  # store AI-generated questions as list of dicts

    def __str__(self):
        return f"Trivia for {self.date}"
    
    def get_questions(self):
        return self.questions or []