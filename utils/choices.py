from django.db import models

class InsightType(models.TextChoices):
    Insight = "insight", "Insight"
    MOOD = "mood", "Mood Insight"
    AFFIRMATION = "affirmation", "Affirmation"
    OTHER = "other", "Other"