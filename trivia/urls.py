from rest_framework.routers import DefaultRouter
from .views import TriviaProfileViewSet, TriviaQuestionViewSet, TriviaAnswerViewSet, TriviaSessionViewSet

router = DefaultRouter()
router.register(r'profile', TriviaProfileViewSet, basename='trivia-profile')
router.register(r'questions', TriviaQuestionViewSet, basename='trivia-questions')
router.register(r'answers', TriviaAnswerViewSet, basename='trivia-answers')
router.register(r'sessions', TriviaSessionViewSet, basename='trivia-sessions')

urlpatterns = router.urls