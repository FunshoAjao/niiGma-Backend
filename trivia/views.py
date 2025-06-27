from datetime import date
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from common.responses import CustomErrorResponse, CustomSuccessResponse
from trivia.choices import TriviaSessionTypeChoices
from trivia.services.tasks import TriviaAIAssistant
from .models import  DailyTriviaSet, TriviaProfile, TriviaSession, TriviaQuestion
from .serializers import SubmitAnswerSerializer, TriviaProfileSerializer, TriviaSessionSerializer
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound

class TriviaSessionViewSet(viewsets.ModelViewSet):
    queryset = TriviaSession.objects.all()
    serializer_class = TriviaSessionSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        raise NotFound()
    
    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)
    
    def get_profile(self, user):
        return TriviaProfile.objects.get_or_create(user=user)[0]
    
    @action(
        detail=False,
        methods=["get"],
        url_path="questions_from_ai",
        permission_classes=[IsAuthenticated]
    )
    def questions_from_ai(self, request):
        """
        Generate trivia questions using AI.
        This is a placeholder for the actual AI question generation logic.
        """
        user = request.user
        questions = TriviaAIAssistant(user).generate_questions_ai()
        return CustomSuccessResponse(data=questions)
    
    @action(
        methods=["get"],
        detail=False,
        url_path="profile",
        permission_classes=[IsAuthenticated],
        serializer_class=TriviaProfileSerializer
    )
    def trivia_profile(self, request):
        """
        Get the trivia profile for the authenticated user.
        Returns whether the user can play trivia today based on mood logging."""
        profile = self.get_profile(request.user)
        serializer = TriviaProfileSerializer(profile)

        today = timezone.now().date()
        can_play = profile.has_used_any_feature_today and profile.last_played != today

        data = serializer.data
        data["can_play"] = can_play
        return CustomSuccessResponse(data=data)
    
    @action(detail=False, methods=["get"], url_path="start_trivia")
    def start_trivia(self, request):
        user = request.user
        today = date.today()
        is_subscribed = False  # Replace with real check later

        if not is_subscribed:
            session = self._handle_free_trivia(user, today)
        else:
            session = self._handle_premium_trivia(user, today)

        return CustomSuccessResponse(data=TriviaSessionSerializer(session).data)


    def _handle_free_trivia(self, user, today):
        if TriviaSession.objects.filter(user=user, source="free", started_at__date=today).exists():
            raise CustomErrorResponse(message="Daily trivia already taken.", status=400)

        try:
            daily = DailyTriviaSet.objects.get(date=today)
        except DailyTriviaSet.DoesNotExist:
            raise CustomErrorResponse(message="Today's trivia is not available.", status=400)

        with transaction.atomic():
            session = TriviaSession.objects.create(user=user, source=TriviaSessionTypeChoices.Free)
            for q in daily.questions:
                TriviaQuestion.objects.create(
                    session=session,
                    question_text=q["question"],
                    choices=q["choices"],
                    correct_choice=q["correct_choice"],
                    explanation=q["explanation"]
                )
            self._update_profile_after_start(user, today)
            return session

    def _handle_premium_trivia(self, user, today):
        session = TriviaSession.objects.create(user=user, source=TriviaSessionTypeChoices.Premium)
        questions = TriviaAIAssistant(user).generate_questions_ai(3)
        for q in questions:
            TriviaQuestion.objects.create(
                session=session,
                question_text=q["question"],
                choices=q["choices"],
                correct_choice=q["correct_choice"],
                explanation=q["explanation"]
            )
        self._update_profile_after_start(user, today)
        return session

    def _update_profile_after_start(self, user, today):
        profile, _ = TriviaProfile.objects.get_or_create(user=user)
        profile.last_played = today
        profile.total_quizzes_played += 1
        profile.save()


    @action(
        detail=True, methods=["post"],
        url_path="submit_answer", 
        serializer_class=SubmitAnswerSerializer
    )
    def submit_answer(self, request, pk=None):
        """
        Submit an answer for a trivia question in the session.
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors, status=400)
        
        profile = self.get_profile(request.user)
        
        question_id = serializer.validated_data["question_id"]
        answer = serializer.validated_data["answer"]
        try:
            question = TriviaQuestion.objects.get(id=question_id, session_id=pk)
        except TriviaQuestion.DoesNotExist:
            return CustomErrorResponse(message= "Invalid question.", status=404)
        
        if question.user_answer is not None:
            return CustomErrorResponse(message="This question has already been answered.", status=400)
        
        question.user_answer = answer
        question.is_correct = (answer == question.correct_choice)
        question.save()
        session = question.session
        
        if session.completed: 
            session.is_completed = True
            session.score = session.calculate_score
            session.save()
            
        if question.is_correct: 
            profile.coins_earned += 5
            profile.total_correct_answers += 1
            profile.save()

        return CustomSuccessResponse(data={"correct": question.is_correct, "explanation": question.explanation})