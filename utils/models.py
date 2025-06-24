import uuid

from django.db import models

from common.models import BaseModel

class DailyWindDownQuote(BaseModel):
    date = models.DateField()
    mood = models.CharField(max_length=50)
    quotes = models.JSONField(default=list, help_text="List of random wind-down quotes")

    def __str__(self):
        return f"Quotes for {self.date}"