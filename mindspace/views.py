from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from .services.tasks import MindSpaceAIAssistant
from .models import MoodMirrorEntry, MindSpaceProfile
from common.responses import CustomErrorResponse, CustomSuccessResponse
from .serializers import MindSpaceProfileSerializer, MoodMirrorEntrySerializer
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated

class MoodMirrorEntryViewSet(viewsets.ModelViewSet):
    queryset = MindSpaceProfile.objects.all()
    serializer_class = MindSpaceProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Return only mood entries related to the authenticated user's mind space.
        """
        return MoodMirrorEntry.objects.filter(
            mind_space__user=self.request.user
        ).order_by('-created_at')

    def create(self, serializer):
        """
        Automatically associate entry with the user's MindSpaceProfile.
        """
        user = self.request.user
        if MindSpaceProfile.objects.filter(user=user).exists():
            print("Mind Space profile already exists for the user.")
            return CustomErrorResponse(
                message="Mind Space profile already exists for the user.",
                status=400)
        serializer.save(user=user)
        return CustomSuccessResponse(
            message="Mood Mirror Entry created successfully.",
            data=serializer.data
        )

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

    @action(
        methods=["post"],
        detail=False,
        url_path="log_mood",
        permission_classes=[IsAuthenticated],
        serializer_class=MoodMirrorEntrySerializer,
    )
    def log_mood(self, request, *args, **kwargs):
        user = request.user
        serializer = MoodMirrorEntrySerializer(data=request.data)
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors, status=400)
        validated_data = serializer.validated_data
        
        if user.mind_space_profile is None:
            return CustomErrorResponse(
                message="Mind Space profile not found for the user.",
                status=404
            )
        
        title = MindSpaceAIAssistant(
            user, user.mind_space_profile
        ).generate_mood_title_with_ai(
            mood=validated_data["mood"],
            reflection=validated_data["reflection"],
            base_64_image=validated_data.get("base_64_image"),
            text=validated_data.get("text", "")
        )
        MoodMirrorEntry.objects.create(
            mind_space=user.mind_space_profile,
            mood=validated_data["mood"],
            reflection=validated_data["reflection"],
            title=title,
            date=validated_data.get("date", timezone.now())
        )
        response = {
            "message": "Mood logged successfully",
            "title": title,
            "mood": validated_data["mood"],
            "reflection": validated_data["reflection"]
        }
        
        return CustomSuccessResponse(data=response, message="Mood logged successfully")
    
    @action(
        methods=["get"],
        detail=False,
        url_path="generate_reflection_note",
        permission_classes=[IsAuthenticated]
    )
    def generate_reflection_note(self, request, *args, **kwargs):
        """
        Generate a reflection note based on the user's mood and reflection.
        """
        user = request.user
        
        try:
            logs = MoodMirrorEntry.objects.filter(
                mind_space__user=user
            ).order_by('-created_at')
            if not logs:
                return CustomSuccessResponse(
                    data=[],
                    message="No mood logs found for the user.",
                    status=404
                )
            
            reflection_note = MindSpaceAIAssistant(
                user, user.mind_space_profile
            ).generate_reflection_note(
                logs
            )
            return CustomSuccessResponse(data=reflection_note, message="Reflection note generated successfully")
        except Exception as e:
            return CustomErrorResponse(message=str(e), status=500)
        
    @action(
        methods=["get"],
        detail=False,
        url_path="generate_insights",
        permission_classes=[IsAuthenticated]
    )
    def generate_insights(self, request, *args, **kwargs):
        """
        Generate personalized insights based on the user's mood history.
        """
        user = request.user
        
        try:
            logs = MoodMirrorEntry.objects.filter(
                mind_space__user=user
            ).order_by('-created_at')
            if not logs:
                return CustomSuccessResponse(
                    data=[],
                    message="No mood logs found for the user.",
                    status=404
                )
            insights = MindSpaceAIAssistant(
                user, user.mind_space_profile
            ).generate_insights(
                logs,
                count=4
            )
            return CustomSuccessResponse(data=insights, message="Insights generated successfully")
        except Exception as e:
            return CustomErrorResponse(message=str(e), status=500)