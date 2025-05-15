from rest_framework import serializers
from .models import CalorieQA, LoggedMeal, SuggestedMeal


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
    
class LoggedMealSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoggedMeal
        fields = ["meal_type", "food_item", "calories"]