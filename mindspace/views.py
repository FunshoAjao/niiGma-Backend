from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import MoodMirrorEntry, MindSpaceProfile
from common.responses import CustomErrorResponse, CustomSuccessResponse
from .serializers import MoodMirrorEntrySerializer
from django.utils import timezone

class MoodMirrorEntryViewSet(viewsets.ModelViewSet):
    queryset = MoodMirrorEntry.objects.all()
    serializer_class = MoodMirrorEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Return only mood entries related to the authenticated user's mind space.
        """
        return MoodMirrorEntry.objects.filter(
            mind_space__user=self.request.user
        ).order_by('-created_at')

    def perform_create(self, serializer):
        """
        Automatically associate entry with the user's MindSpaceProfile.
        """
        user = self.request.user
        mind_space_profile = getattr(user, "mind_space_profile", None)
        if not mind_space_profile:
            mind_space_profile = MindSpaceProfile.objects.create(user=user)
        serializer.save(mind_space=mind_space_profile)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return CustomSuccessResponse(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return CustomSuccessResponse(data=serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create a new mood mirror entry.
        """
        return super().create(request, *args, **kwargs)
