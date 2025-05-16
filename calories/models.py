from django.db import models
from accounts.models import User
from common.models import BaseModel

MEAL_TYPES = [
        ("breakfast", "Breakfast"),
        ("lunch", "Lunch"),
        ("dinner", "Dinner")
    ]

INTENSITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]

class CalorieQA(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="calorie_qa")
    goal = models.CharField(max_length=100)  # body goals
    activity_level = models.CharField(max_length=100)
    current_weight = models.FloatField()
    goal_weight = models.FloatField()
    eating_style = models.CharField(max_length=400)
    reminder = models.CharField(max_length=400)
    allow_smart_food_suggestions = models.BooleanField(default=False)
    goal_timeline = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f'{self.user} calorie'
    
    class Meta:
        ordering = ("-created_at",)
        
    @property
    def days_left(self):
        return (self.goal_timeline - self.created_at).days

    @property
    def daily_calorie_target(self):
        # Simplified: 7700 kcal = 1kg
        weight_diff = self.goal_weight - self.current_weight
        total_calories_needed = 7700 * abs(weight_diff)
        days = self.days_left
        return int(total_calories_needed / days) if days > 0 else 0

class SuggestedMeal(BaseModel):
    calorie_goal = models.ForeignKey(CalorieQA, on_delete=models.CASCADE)
    date = models.DateTimeField()
    meal_type = models.CharField(max_length=10, choices=MEAL_TYPES)
    meal_name = models.CharField(max_length=200, blank=True, null=True)
    food_item = models.CharField(max_length=100)
    calories = models.IntegerField()
    protein = models.IntegerField(default=0)
    carbs = models.IntegerField(default=0)
    fats = models.IntegerField(default=0)
    
    def __str__(self):
        return f'{self.calorie_goal} suggested meal'

    class Meta:
        unique_together = ("calorie_goal", "created_at", "meal_type", "food_item")
        
class SuggestedWorkout(BaseModel):
    calorie_goal = models.ForeignKey(CalorieQA, on_delete=models.CASCADE)
    date = models.DateTimeField()
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    estimated_calories_burned = models.IntegerField()
    intensity = models.CharField(max_length=10, choices=INTENSITY_CHOICES)
    duration_minutes = models.PositiveIntegerField()

    class Meta:
        unique_together = ("calorie_goal", "date")
        
    def __str__(self):
        return f"{self.title} ({self.date})"


class LoggedMeal(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    meal_type = models.CharField(max_length=10, choices=MEAL_TYPES)
    food_item = models.CharField(max_length=100)
    calories = models.IntegerField()
    date = models.DateTimeField(blank=True, null=True)
    protein = models.IntegerField(default=0)
    carbs = models.IntegerField(default=0)
    fats = models.IntegerField(default=0)
    
    class Meta:
        ordering = ("-created_at",)
        
    def __str__(self):
        return f'{self.user} logged meal'
    
class LoggedWorkout(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    workout_type = models.CharField(max_length=200)
    duration_minutes = models.IntegerField()
    calories_burned = models.IntegerField()

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user}'s workout on {self.date}"