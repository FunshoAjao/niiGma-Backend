from django.db import models
from django.contrib.auth import get_user_model
from accounts.models import User

class Reminder(models.Model):
    REMINDER_TYPE_CHOICES = [
        ('meal', 'Meal'),
        ('water', 'Water'),
        ('exercise', 'Exercise'),
        ('check-in', 'Check-in'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=REMINDER_TYPE_CHOICES)
    time = models.TimeField()
    message = models.TextField()
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user} - {self.type} at {self.time}"
