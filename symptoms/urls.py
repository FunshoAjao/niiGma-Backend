from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FeverTriggersViewSet, SensationDescriptionViewSet, SymptomSessionViewSet, SymptomLocationViewSet, SymptomViewSet, SymptomAnalysisView

router = DefaultRouter()
router.register(r'sessions', SymptomSessionViewSet, basename='session')
router.register(r'body_locations', SymptomLocationViewSet, basename='body_location')
router.register(r'body_symptoms', SymptomViewSet, basename='body_symptom')
router.register(r'analyze_symptoms', SymptomAnalysisView, basename='analyze_symptoms')
router.register(r'sensation-descriptions', SensationDescriptionViewSet, basename='sensation-description')
router.register(r'fever-triggers', FeverTriggersViewSet, basename='fever-trigger')

# urlpatterns = [
#     # path('', include(router.urls)),
#     path('analysis/<int:pk>/', SymptomAnalysisView.as_view(), name='symptom-analysis'),
# ]
urlpatterns = router.urls