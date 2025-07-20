from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from common.responses import CustomErrorResponse, CustomSuccessResponse

from .serializers import TestPushNotificationSerializer
from utils.helpers.fcm import PushNotificationService  # Adjust as needed


class SendPushNotificationView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TestPushNotificationSerializer

    def post(self, request):
        serializer = TestPushNotificationSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        device_token = data['device_token'] 

        # Send push
        push_service = PushNotificationService(data['device_type'], data['device_type'])
        push_service.send_push_notification(
            title=data["title"],
            body=data["body"],
            registration_token=device_token,
            route=data.get("route")
        )

        return CustomSuccessResponse(message="Push notification sent", status=status.HTTP_200_OK)
