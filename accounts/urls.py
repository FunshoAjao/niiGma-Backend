from django.urls import path
from .views import UserViewSet
from rest_framework.routers import DefaultRouter
from rest_framework import routers

# Define the router
router = DefaultRouter()

urlpatterns = [
    
]

# Register ViewSets
router = routers.SimpleRouter(trailing_slash=False)
router.register(r'user', UserViewSet)

# Add router URLs to urlpatterns
urlpatterns += router.urls
