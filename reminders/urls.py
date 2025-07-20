from django.urls import path
from .views import SendPushNotificationView

urlpatterns = [
    path('send-push/', SendPushNotificationView.as_view(), name='send-push'),
]
