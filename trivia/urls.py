from rest_framework.routers import DefaultRouter
from .views import TriviaSessionViewSet

router = DefaultRouter()
router.register(r'trivia_sessions', TriviaSessionViewSet, basename='trivia_sessions')

urlpatterns = router.urls