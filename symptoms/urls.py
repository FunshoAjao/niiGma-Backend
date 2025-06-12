from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SymptomSessionViewSet, SymptomLocationViewSet, SymptomViewSet, SymptomAnalysisView

router = DefaultRouter()
router.register(r'sessions', SymptomSessionViewSet, basename='session')
router.register(r'body_locations', SymptomLocationViewSet, basename='body_location')
router.register(r'body_symptoms', SymptomViewSet, basename='body_symptom')

urlpatterns = [
    path('', include(router.urls)),
    path('analysis/<int:pk>/', SymptomAnalysisView.as_view(), name='symptom-analysis'),
]
