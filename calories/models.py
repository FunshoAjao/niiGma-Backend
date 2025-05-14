from django.db import models
from accounts.models import User
from common.models import BaseModel

class CalorieQA(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    goal = models.CharField(max_length=100)
    activity_level = models.CharField(max_length=100)
    weight = models.FloatField()
    goal_weight = models.FloatField()
    
    def __str__(self):
        return f'{self.user} calorie'
    
    class Meta:
        ordering = ("-created_at",)
