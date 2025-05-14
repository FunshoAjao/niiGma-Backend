from rest_framework import serializers
from .models import CalorieQA


class CalorieSerializer(serializers.ModelSerializer):

    class Meta:
        model = CalorieQA
        fields = '__all__'
        read_only_fields = [
            "user", 'id', 'created_at', 'updated_at'
        ]
        
class CalorieAISerializer(serializers.Serializer):
    prompt = serializers.CharField()