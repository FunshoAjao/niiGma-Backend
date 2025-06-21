from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import TriviaProfile, TriviaQuestion, TriviaAnswer, TriviaSession
from .serializers import (
    TriviaProfileSerializer, TriviaQuestionSerializer,
    TriviaAnswerSerializer, TriviaSessionSerializer
)
from django.utils import timezone
import random

class TriviaProfileViewSet(viewsets.ModelViewSet):
    queryset = TriviaProfile.objects.all()
    serializer_class = TriviaProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class TriviaQuestionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TriviaQuestion.objects.all()
    serializer_class = TriviaQuestionSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def daily_quiz(self, request):
        questions = list(self.queryset)
        random.shuffle(questions)
        return Response(TriviaQuestionSerializer(questions[:3], many=True).data)

class TriviaAnswerViewSet(viewsets.ModelViewSet):
    queryset = TriviaAnswer.objects.all()
    serializer_class = TriviaAnswerSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        question = serializer.validated_data['question']
        selected = serializer.validated_data['selected_option']
        is_correct = (selected == question.correct_option)
        serializer.save(user=self.request.user, is_correct=is_correct)

class TriviaSessionViewSet(viewsets.ModelViewSet):
    queryset = TriviaSession.objects.all()
    serializer_class = TriviaSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)