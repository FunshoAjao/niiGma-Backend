from rest_framework import serializers
from .models import TriviaProfile, TriviaQuestion, TriviaAnswer, TriviaSession

class TriviaProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TriviaProfile
        fields = '__all__'

class TriviaQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TriviaQuestion
        exclude = ['correct_option', 'explanation']  # To prevent sending answer upfront

class TriviaAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TriviaAnswer
        fields = '__all__'
        read_only_fields = ('is_correct',)

class TriviaSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TriviaSession
        fields = '__all__'