from django.db import models
from accounts.models import User
from common.models import BaseModel

class TriviaProfile(BaseModel):
    """
    Tracks user-specific trivia settings and history.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="trivia_profile")
    last_played = models.DateField(null=True, blank=True)
    coins_earned = models.IntegerField(default=0)
    total_quizzes_played = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.email} - Trivia Profile"

class TriviaSession(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="trivia_sessions")
    started_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)
    source = models.CharField(max_length=20, choices=[("free", "Free"), ("premium", "Premium")])
    score = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.email} - {self.started_at.date()}"

class TriviaQuestion(BaseModel):
    session = models.ForeignKey(TriviaSession, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()
    choices = models.JSONField()
    correct_choice = models.CharField(max_length=1)
    explanation = models.TextField(blank=True)
    user_answer = models.CharField(max_length=1, null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return self.question_text

class DailyTriviaSet(BaseModel):
    date = models.DateField()
    category = models.CharField(max_length=100)  # e.g. "general", "fitness"
    questions = models.JSONField()  # store AI-generated questions as list of dicts

    def __str__(self):
        return f"Trivia for {self.date}"