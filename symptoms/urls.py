from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SymptomSessionViewSet, SymptomLocationViewSet, SymptomViewSet, SymptomAnalysisView

router = DefaultRouter()
router.register(r'sessions', SymptomSessionViewSet, basename='session')
router.register(r'locations', SymptomLocationViewSet, basename='location')
router.register(r'symptoms', SymptomViewSet, basename='symptom')

urlpatterns = [
    path('', include(router.urls)),
    path('analysis/<int:pk>/', SymptomAnalysisView.as_view(), name='symptom-analysis'),
]
