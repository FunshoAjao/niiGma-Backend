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

class TriviaQuestion(BaseModel):
    """
    Stores trivia questions and correct answers.
    """
    question = models.TextField()
    explanation = models.TextField(blank=True, null=True)
    
    option_1 = models.CharField(max_length=255)
    option_2 = models.CharField(max_length=255)
    option_3 = models.CharField(max_length=255)
    option_4 = models.CharField(max_length=255)
    
    correct_option = models.PositiveSmallIntegerField(
        choices=[(1, "option_1"), (2, "option_2"), (3, "option_3"), (4, "option_4")]
    )

    def __str__(self):
        return self.question[:50] + "..."

class TriviaAnswer(BaseModel):
    """
    Logs a user's answer to a trivia question.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="trivia_answers")
    question = models.ForeignKey(TriviaQuestion, on_delete=models.CASCADE, related_name="answers")
    selected_option = models.PositiveSmallIntegerField()
    is_correct = models.BooleanField()
    
    def __str__(self):
        return f"{self.user.email} - Q{self.question.id} - {'Correct' if self.is_correct else 'Wrong'}"

class TriviaSession(BaseModel):
    """
    Stores metadata for a quiz session (e.g., 3–5 questions per day).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="trivia_sessions")
    date = models.DateField()
    score = models.IntegerField()
    coins_earned = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - {self.date} - {self.score} pts"
