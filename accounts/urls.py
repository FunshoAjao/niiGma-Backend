from django.urls import path
from .views import PromptHistoryView, UserViewSet
from rest_framework.routers import DefaultRouter
from rest_framework import routers

# Define the router
router = DefaultRouter()

urlpatterns = [
    path('prompt_history/', PromptHistoryView.as_view(), name='prompt_history'),
]

# Register ViewSets
router = routers.SimpleRouter(trailing_slash=False)
router.register(r'user', UserViewSet)

# Add router URLs to urlpatterns
urlpatterns += router.urls
