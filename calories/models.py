from django.db import models
from accounts.models import User
from common.models import BaseModel

class CalorieQA(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    goal = models.CharField(max_length=100)  # body goals
    activity_level = models.CharField(max_length=100)
    current_weight = models.FloatField()
    goal_weight = models.FloatField()
    eating_style = models.CharField(max_length=400)
    reminder = models.CharField(max_length=400)
    allow_smart_food_suggestions = models.BooleanField(default=False)
    
    def __str__(self):
        return f'{self.user} calorie'
    
    class Meta:
        ordering = ("-created_at",)
