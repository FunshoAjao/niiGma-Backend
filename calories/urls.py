from django.urls import path
from .views import CalorieViewSet
from rest_framework.routers import DefaultRouter
from rest_framework import routers

router = DefaultRouter()

urlpatterns = [
    
]

router = routers.SimpleRouter(trailing_slash=False)
router.register(r'', CalorieViewSet)

urlpatterns += router.urls
