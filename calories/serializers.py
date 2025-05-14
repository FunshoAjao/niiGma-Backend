from rest_framework import serializers
from .models import CalorieQA


class CalorieSerializer(serializers.ModelSerializer):

    class Meta:
        model = CalorieQA
        fields = '__all__'
        
class CalorieAISerializer(serializers.Serializer):
    prompt = serializers.CharField()