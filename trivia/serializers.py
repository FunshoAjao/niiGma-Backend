from rest_framework import serializers
from .models import TriviaQuestion, TriviaSession

class TriviaQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TriviaQuestion
        fields = "__all__"
        read_only_fields = ("session", "question_text", "choices", "correct_choice", "explanation")

class TriviaSessionSerializer(serializers.ModelSerializer):
    questions = TriviaQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = TriviaSession
        fields = "__all__"