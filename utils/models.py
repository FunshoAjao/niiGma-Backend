import uuid

from django.db import models

from accounts.models import User
from common.models import BaseModel
from utils.choices import InsightType

class DailyWindDownQuote(BaseModel):
    date = models.DateField()
    mood = models.CharField(max_length=50)
    quotes = models.JSONField(default=list, help_text="List of random wind-down quotes")

    def __str__(self):
        return f"Quotes for {self.date}"

class UserAIInsight(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mood_insights")
    context_tag = models.CharField(max_length=50, blank=True, null=True, help_text="Context tag for the insight")
    date = models.DateField()
    insight_type = models.CharField(max_length=20, choices=InsightType.choices)
    insights = models.JSONField(default=list, help_text="List of daily insights/affirmations")

    def __str__(self):
        return f"{self.user.email} - {self.context_tag} @{self.date} - {self.insight_type}"
    
    class Meta:
        unique_together = ("user", "date", "insight_type")
        indexes = [
            models.Index(fields=["user", "date", "context_tag", "insight_type"]),
        ]
