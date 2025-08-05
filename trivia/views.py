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
    
    def get_paginated_response(self, data):
        return Response({
            'status': 'success',
            'message': '',
            'data': {
                'count': self.paginator.page.paginator.count,
                'next': self.paginator.get_next_link(),
                'previous': self.paginator.get_previous_link(),
                'results': data
            }
        })

    def get_paginated_response_for_none_records(self, data):
        return Response({
            'status': 'success',
            'message': 'No user records found.',
            'data': {
                'count': 0,
                'next': None,
                'previous': None,
                'results': data
            }
        })
    
    def get(self, request, *args, **kwargs):
        """
        Override the default GET method to return only sessions for the authenticated user.
        """
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return self.get_paginated_response_for_none_records(data=serializer.data)

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
        user=request.user

        today = timezone.now().date()
        can_play = profile.has_used_any_feature_today and profile.last_played != today

        data = serializer.data
        data["can_play"] = can_play
        user.is_trivia_setup = True
        user.save()
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
        from rest_framework import serializers
        if TriviaSession.objects.filter(user=user, source="free", started_at__date=today).exists():
            raise serializers.ValidationError({'message':"Daily trivia already taken.", "status":"failed"}, code=400)

        try:
            daily = DailyTriviaSet.objects.get(date=today)
        except DailyTriviaSet.DoesNotExist:
            raise serializers.ValidationError({'message':"Today's trivia is not available.", "status":"failed"}, code=400)

        with transaction.atomic():
            session = TriviaSession.objects.create(user=user, source=TriviaSessionTypeChoices.Free)
            questions = daily.questions.order_by('?')[:5]  # randomly select 5 questions
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

    def _handle_premium_trivia(self, user, today):
        session = TriviaSession.objects.create(user=user, source=TriviaSessionTypeChoices.Premium)
        questions = TriviaAIAssistant(user).generate_questions_ai(4)
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