from django.db import models
from accounts.models import User
from calories.choices import ReminderChoices
from common.models import BaseModel
from django.utils import timezone

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

WEIGHT_UNITS = [
    ("kg", "Kilograms"),
    ("lb", "Pounds")
]

MEASUREMENT_UNITS = [
    ("servings", "Serving"),
    ("grams", "Gram"),
    ("slice", "Slice"),
]

class UserCalorieStreak(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="calorie_streak")
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_streak_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} - Current: {self.current_streak}, Longest: {self.longest_streak}"


class CalorieQA(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="calorie_qa")
    goal = models.CharField(max_length=100)  # body goals
    activity_level = models.CharField(max_length=100)
    current_weight = models.FloatField()
    goal_weight = models.FloatField()
    weight_unit = models.CharField(max_length=5, choices=WEIGHT_UNITS, default="kg")
    eating_style = models.CharField(max_length=400)
    reminder = models.CharField(max_length=400, choices=ReminderChoices, default=ReminderChoices.Daily)
    allow_smart_food_suggestions = models.BooleanField(default=False)
    goal_timeline = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f'{self.user.first_name} calorie'
    
    class Meta:
        ordering = ("-created_at",)
        
    @property
    def days_left(self):
        if not self.goal_timeline:
            return 0
        days = (self.goal_timeline.date() - timezone.now().date()).days
        return max(days, 0) 

    @property
    def daily_calorie_target(self):
        # Simplified: 7700 kcal = 1kg
        weight_diff = self.goal_weight - self.current_weight
        total_calories_needed = 7700 * abs(weight_diff)
        days = self.days_left
        return int(total_calories_needed / days) if days > 0 else 0
    
    @property
    def macro_nutrient_targets(self):
        calorie_target = self.daily_calorie_target

        protein_pct = 0.25
        fat_pct = 0.30
        carbs_pct = 0.45

        protein_target = int((calorie_target * protein_pct) / 4)  # 4 kcal/g
        fat_target = int((calorie_target * fat_pct) / 9)          # 9 kcal/g
        carbs_target = int((calorie_target * carbs_pct) / 4)      # 4 kcal/g

        return {
            "protein": protein_target,
            "fat": fat_target,
            "carbs": carbs_target,
        }


class SuggestedMeal(BaseModel):
    calorie_goal = models.ForeignKey(CalorieQA, on_delete=models.CASCADE)
    date = models.DateTimeField(null=True)
    meal_type = models.CharField(max_length=10, choices=MEAL_TYPES)
    meal_name = models.CharField(max_length=200, blank=True, null=True)
    food_item = models.CharField(max_length=100)
    calories = models.IntegerField()
    protein = models.IntegerField(default=0)
    carbs = models.IntegerField(default=0)
    fats = models.IntegerField(default=0)
    is_template = models.BooleanField(default=False)  # Distinguish reusable meals
    
    def __str__(self):
        return f'{self.calorie_goal.user.first_name} - {self.meal_type} {"(template)" if self.is_template else ""}'


    class Meta:
        unique_together = ("calorie_goal", "created_at", "meal_type", "food_item")
        ordering = ("-created_at",)
        
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
    image_url = models.URLField(blank=True, null=True)
    measurement_unit = models.CharField(max_length=10, choices=MEASUREMENT_UNITS, default="serving")
    number_of_servings_or_gram_or_slices = models.PositiveBigIntegerField(default=1)
    
    class Meta:
        ordering = ("-created_at",)
        
    def __str__(self):
        return f'{self.user} logged meal'
    
class LoggedWorkout(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    title = models.CharField(max_length=200)
    duration_minutes = models.IntegerField()
    estimated_calories_burned = models.IntegerField()
    intensity = models.CharField(max_length=10, choices=INTENSITY_CHOICES, default="low")
    description = models.TextField(blank=True, null=True)
    steps = models.IntegerField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user}'s workout on {self.date}"