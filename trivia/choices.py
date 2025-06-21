from django.db import models
    
class TriviaSessionTypeChoices(models.TextChoices):
    Free = "free", "Free"
    Premium = "premium", "Premium"