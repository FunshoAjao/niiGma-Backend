from rest_framework import serializers
from .models import TriviaProfile, TriviaQuestion, TriviaSession

class TriviaQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TriviaQuestion
        fields = ["id", "session", "question_text", "choices", "correct_choice", "explanation", "user_answer", "is_correct"]
        read_only_fields = ("session", "question_text", "choices", "correct_choice", "explanation")

class TriviaSessionSerializer(serializers.ModelSerializer):
    questions = TriviaQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = TriviaSession
        fields = ["id", "user", "started_at", "is_completed", "source", "score", "questions", "created_at", "updated_at"]
        read_only_fields = ("user", "started_at", "is_completed", "score", "created_at", "updated_at")
        
class SubmitAnswerSerializer(serializers.Serializer):
    question_id = serializers.UUIDField(required=True)
    answer = serializers.CharField(max_length=1, required=True)

    def validate_answer(self, value):
        if value not in ["A", "B", "C", "D"]:
            raise serializers.ValidationError("Answer must be one of A, B, C, or D.")
        return value
    
class TriviaProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TriviaProfile
        fields = ["last_played", "coins_earned", "total_quizzes_played", "total_correct_answers", "referral_count", "seven_day_streak"]