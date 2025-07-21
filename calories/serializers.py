from rest_framework import serializers

from django.db import models

from calories.choices import ReminderChoices
from .models import CalorieQA, LoggedMeal, LoggedWorkout, SuggestedMeal, SuggestedWorkout, UserCalorieStreak

class FlexibleChoiceField(serializers.ChoiceField):
    def to_internal_value(self, data):
        # First, check if data matches the valid values
        if data in self.choices:
            return data

        # Then, try matching display labels (case-insensitive)
        for key, label in self.choices.items():
            if str(label).lower() == str(data).lower():
                return key

        self.fail("invalid_choice", input=data)

    def to_representation(self, value):
        return self.choices.get(value, value)

class MealSource(models.TextChoices):
    Barcode = "barcode", "Barcode"
    Manual = "manual", "Manual"
    AI = "ai", "AI"
    Scanned = "scanned", "Scanned"

class CalorieSerializer(serializers.ModelSerializer):
    reminder = FlexibleChoiceField(choices=ReminderChoices.choices, default=ReminderChoices.Daily)
    class Meta:
        model = CalorieQA
        fields = '__all__'
        read_only_fields = [
            "user", 'id', 'created_at', 'updated_at'
        ]
        
class CalorieAISerializer(serializers.Serializer):
    prompt = serializers.CharField()
    
class SuggestedMealSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuggestedMeal
        fields = ["meal_type", "food_item", "calories", "protein", "carbs", "fats", 'date', 'id']
        read_only_fields = [
            "calorie_goal", "date", "id", "created_at", "updated_at"
        ]
        
class SuggestedWorkoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuggestedWorkout
        fields = [
            "id",
            "calorie_goal",
            "date",
            "title",
            "description",
            "duration_minutes",
            "intensity",
            "estimated_calories_burned",
            "created_at",  # assuming BaseModel has this
            "updated_at"
        ]
        read_only_fields = ("created_at", "updated_at")
    
class LoggedMealSerializer(serializers.ModelSerializer):
    meal_source = serializers.ChoiceField(choices=MealSource.choices, default=MealSource.Manual)
    barcode = serializers.CharField(required=False, allow_null=True)
    image_url = serializers.CharField(allow_null=True)
    food_item = serializers.CharField(allow_null=True, allow_blank=True)
    number_of_servings_or_gram_or_slices = serializers.IntegerField(allow_null=True)
    class Meta:
        model = LoggedMeal
        fields = ['meal_type', 'food_item', 'date', 'calories', 'protein', 'carbs', 'fats',
                  'meal_source', 'image_url', 'number_of_servings_or_gram_or_slices', 'measurement_unit', 'barcode', 'id']
        read_only_fields = ['calories', 'protein', 'carbs', 'fats', 'id', 'user', 'created_at', 'updated_at']  
        
    def validate(self, data):
        meal_source = data.get('meal_source')
        barcode = data.get('barcode')
        image_url = data.get('image_url')
        food_item = data.get('food_item')
        
        if meal_source != MealSource.Scanned and food_item is None:
            raise serializers.ValidationError(
                {"message": "food item is required!", "status": "failed"},
                code=400
            )
        
        if meal_source == MealSource.Barcode and not barcode:
            raise serializers.ValidationError(
                {"message": "Barcode is required!", "status": "failed"},
                code=400
            )
        
        if meal_source == MealSource.Scanned and not image_url:
            raise serializers.ValidationError(
                {"message": "Image is required!", "status": "failed"},
                code=400
            )

        return data
        
class LoggedWorkoutSerializer(serializers.ModelSerializer):
    steps = serializers.IntegerField(required=False)
    class Meta:
        model = LoggedWorkout
        fields = [
            "id",
            "user",
            "date",
            "title",
            "intensity",
            "description",
            "duration_minutes",
            "estimated_calories_burned",
            "created_at",
            "updated_at",
            "steps"
        ]
        read_only_fields = ("created_at", "updated_at", "user", "estimated_calories_burned")
        
class SampleLoggedWorkoutSerializer(serializers.Serializer):
    description = serializers.CharField(required=True)
    
class SampleLoggedMealSerializer(serializers.Serializer):
    food_item = serializers.CharField(required=True)
    meal_source = serializers.ChoiceField(choices=MealSource.choices, default=MealSource.Manual)
    barcode = serializers.CharField(required=False, allow_null=True)
    image_url = serializers.ImageField(required=False, allow_null=True)
    
    def validate(self, data):
        meal_source = data.get('meal_source')
        barcode = data.get('barcode')

        if meal_source == MealSource.Barcode and not barcode:
            raise serializers.ValidationError(
                {"message": "Barcode is required!", "status": "failed"},
                code=400
            )

        return data
    
class CalorieStreakSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCalorieStreak
        fields = ['current_streak', 'longest_streak', 'last_streak_date']
