from datetime import date
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from common.responses import CustomErrorResponse, CustomSuccessResponse
from trivia.services.tasks import TriviaAIAssistant
from .models import  DailyTriviaSet, TriviaSession, TriviaQuestion
from .serializers import TriviaSessionSerializer
from django.db import transaction

class TriviaSessionViewSet(viewsets.ModelViewSet):
    queryset = TriviaSession.objects.all()
    serializer_class = TriviaSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(detail=False, methods=["get"], url_path="start")
    def start_trivia(self, request):
        user = request.user
        today = date.today()
        is_subscribed = hasattr(user, "subscription") and user.subscription.is_active  # Adjust to your model

        # Free user logic
        if not is_subscribed:
            if TriviaSession.objects.filter(user=user, source="free", started_at__date=today).exists():
                return CustomErrorResponse(message="Daily trivia already taken.", status=400)

            daily, _ = DailyTriviaSet.objects.get_or_create(date=today, defaults={
                "questions": TriviaAIAssistant(request.user).generate_questions_ai(3)
            })

            with transaction.atomic():
                session = TriviaSession.objects.create(user=user, source="free")
                for q in daily.questions:
                    TriviaQuestion.objects.create(
                        session=session,
                        question_text=q["question"],
                        choices=q["choices"],
                        correct_choice=q["correct_choice"],
                        explanation=q["explanation"]
                    )
        else:
            # Premium logic - generate from AI each time (hook with OpenAI or similar)
            session = TriviaSession.objects.create(user=user, source="premium")
            questions = TriviaAIAssistant(request.user).generate_questions_ai(3)
            for q in questions:
                TriviaQuestion.objects.create(
                    session=session,
                    question_text=q["question"],
                    choices=q["choices"],
                    correct_choice=q["correct_choice"],
                    explanation=q["explanation"]
                )

        return CustomSuccessResponse(data=TriviaSessionSerializer(session).data)

    @action(detail=True, methods=["post"], url_path="submit-answer")
    def submit_answer(self, request, pk=None):
        question_id = request.data.get("question_id")
        answer = request.data.get("answer")
        try:
            question = TriviaQuestion.objects.get(id=question_id, session_id=pk)
        except TriviaQuestion.DoesNotExist:
            return CustomErrorResponse(message= "Invalid question.", status=404)

        question.user_answer = answer
        question.is_correct = (answer == question.correct_choice)
        question.save()

        return CustomSuccessResponse(data={"correct": question.is_correct, "explanation": question.explanation})
