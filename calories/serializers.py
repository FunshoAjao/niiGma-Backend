from rest_framework import serializers

from django.db import models
from .models import CalorieQA, LoggedMeal, LoggedWorkout, SuggestedMeal, SuggestedWorkout

class MealSource(models.TextChoices):
    Barcode = "barcode", "Barcode"
    Manual = "manual", "Manual"
    AI = "ai", "AI"
    Scanned = "scanned", "Scanned"

class CalorieSerializer(serializers.ModelSerializer):

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
        fields = ["meal_type", "food_item", "calories", "protein", "carbs", "fats", 'date']
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
    barcode = serializers.CharField(required=False)
    class Meta:
        model = LoggedMeal
        fields = ['meal_type', 'food_item', 'date', 'calories', 'protein', 'carbs', 'fats',
                  'meal_source', 'image_url', 'number_of_servings', 'measurement_unit', 'barcode']
        read_only_fields = ['calories', 'protein', 'carbs', 'fats', 'id', 'user', 'created_at', 'updated_at']  
        
    def validate(self, data):
        meal_source = data.get('meal_source')
        barcode = data.get('barcode')

        if meal_source == MealSource.Barcode and not barcode:
            raise serializers.ValidationError(
                {"message": "Barcode is required!", "status": "failed"},
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