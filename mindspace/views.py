from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from .services.tasks import MindSpaceAIAssistant, create_sound_space_playlist
from .models import *
from common.responses import CustomErrorResponse, CustomSuccessResponse
from .serializers import *
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db import transaction

class MindSpaceViewSet(viewsets.ModelViewSet):
    queryset = MindSpaceProfile.objects.all()
    serializer_class = MindSpaceProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_paginated_response(self, data):
        return Response({
            'count': self.paginator.page.paginator.count,
            'next': self.paginator.get_next_link(),
            'previous': self.paginator.get_previous_link(),
            'status': 'success',
            'entity': data,
            'message': ''
        })

    def get_paginated_response_for_none_records(self, data):
        return Response({
            'count': 0,
            'next': None,
            'previous': None,
            'status': 'success',
            'entity': data,
            'message': 'No project records found.'
        })

    def get_queryset(self):
        """
        Return only mood entries related to the authenticated user's mind space.
        """
        return MoodMirrorEntry.objects.filter(
            mind_space__user=self.request.user
        ).order_by('-created_at')

    @transaction.atomic
    def create(self, request):
        """
        Automatically associate entry with the user's MindSpaceProfile.
        """
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors)
        user = self.request.user
        if MindSpaceProfile.objects.filter(user=user).exists():
            print("Mind Space profile already exists for the user.")
            return CustomErrorResponse(
                message="Mind Space profile already exists for the user.",
                status=400)
        mindspace_profile = serializer.save(user=user)
        user = User.objects.get(id=user.id)
        user.is_mind_space_setup = True
        user.save()
        transaction.on_commit(lambda: create_sound_space_playlist.delay(mindspace_profile.id))
        return CustomSuccessResponse(
            message="Mind space created successfully.",
            data=serializer.data
        )
        
    def update(self, request, *args, **kwargs):
        """
        Update mind space play list.
        """
        instance = self.get_object()
        serializer = self.serializer_class(instance, data=request.data, partial=True, context={'request': request})
        if not serializer.is_valid():
            return CustomErrorResponse(
                message=serializer.errors,
                status=400
            )
        validated_data = serializer.validated_data
        serializer.save(**validated_data)
        return CustomSuccessResponse(
            message="Mind space updated successfully.",
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

class MoodMirrorEntryViewSet(viewsets.ModelViewSet):
    queryset = MindSpaceProfile.objects.all()
    serializer_class = MindSpaceProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_paginated_response(self, data):
        return Response({
            'count': self.paginator.page.paginator.count,
            'next': self.paginator.get_next_link(),
            'previous': self.paginator.get_previous_link(),
            'status': 'success',
            'entity': data,
            'message': ''
        })

    def get_paginated_response_for_none_records(self, data):
        return Response({
            'count': 0,
            'next': None,
            'previous': None,
            'status': 'success',
            'entity': data,
            'message': 'No project records found.'
        })

    def get_queryset(self):
        """
        Return only mood entries related to the authenticated user's mind space.
        """
        return MoodMirrorEntry.objects.filter(
            mind_space__user=self.request.user
        ).order_by('-created_at')

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Automatically associate entry with the user's MindSpaceProfile.
        """
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors)
        user = self.request.user
        if MindSpaceProfile.objects.filter(user=user).exists():
            print("Mind Space profile already exists for the user.")
            return CustomErrorResponse(
                message="Mind Space profile already exists for the user.",
                status=400)
        mindspace_profile = serializer.save(user=user)
        user = User.objects.get(id=user.id)
        user.is_mind_space_setup = True
        user.save()
        transaction.on_commit(lambda: create_sound_space_playlist.delay(mindspace_profile.id))
        return CustomSuccessResponse(
            message="Mood Mirror Entry created successfully.",
            data=serializer.data
        )

    def update(self, request, *args, **kwargs):
        """
        Update mind space .
        """
        instance = self.get_object()
        serializer = self.serializer_class(instance, data=request.data, partial=True, context={'request': request})
        if not serializer.is_valid():
            return CustomErrorResponse(
                message=serializer.errors,
                status=400
            )
        validated_data = serializer.validated_data
        serializer.save(**validated_data)
        return CustomSuccessResponse(
            message="Mind space updated successfully.",
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
                status=200
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
                    status=200
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
        url_path="generate_today_affirmation",
        permission_classes=[IsAuthenticated]
    )
    def generate_today_affirmation(self, request, *args, **kwargs):
        """
        Generate a reflection note based on the user's mood and reflection.
        """
        user = request.user
        
        try:
            logs = MoodMirrorEntry.objects.filter(
                mind_space__user=user, date__date = timezone.now().date()
            ).order_by('-created_at')
            
            if not logs.exists():
                return CustomSuccessResponse(
                    data=[],
                    message="No mood logs found for the user.",
                    status=200
                )
            
            latest_log = logs[0]  # Get the most recent entry
            
            if latest_log.affirmation:
                return CustomSuccessResponse(
                    data=latest_log.affirmation,
                    message="Reflection note already exists.",
                    status=200
                )
            today_affirmation = MindSpaceAIAssistant(
                user, user.mind_space_profile
            ).generate_affirmation(
                latest_log.reflection
            )
            logs.update(affirmation=today_affirmation)
            return CustomSuccessResponse(data=today_affirmation, message="Today's affirmation generated successfully")
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
                    status=200
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
        
class SoundscapePlayViewSet(viewsets.ModelViewSet):
    queryset = SoundscapePlay.objects.all().order_by('-created_at')
    serializer_class = SoundscapePlaySerializer
    permission_classes = [IsAuthenticated]

    def get_paginated_response(self, data):
        return Response({
            'count': self.paginator.page.paginator.count,
            'next': self.paginator.get_next_link(),
            'previous': self.paginator.get_previous_link(),
            'status': 'success',
            'entity': data,
            'message': ''
        })

    def get_paginated_response_for_none_records(self, data):
        return Response({
            'count': 0,
            'next': None,
            'previous': None,
            'status': 'success',
            'entity': data,
            'message': 'No project records found.'
        })
    
    def get_queryset(self):
        return SoundscapePlay.objects.filter(mind_space=self.request.user.mind_space_profile)
    
    def create(self, request, *args, **kwargs):
        """
        Create sound scape play list.
        """
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return CustomErrorResponse(
                message=serializer.errors,
                status=400
            )
        validated_data = serializer.validated_data
        serializer.save(**validated_data)
        return CustomSuccessResponse(
            message="Soundscape Play created successfully.",
            data=serializer.data
        )
        
    def update(self, request, *args, **kwargs):
        """
        Update sound scape play list.
        """
        instance = self.get_object()
        serializer = self.serializer_class(instance, data=request.data, partial=True, context={'request': request})
        if not serializer.is_valid():
            return CustomErrorResponse(
                message=serializer.errors,
                status=400
            )
        validated_data = serializer.validated_data
        serializer.save(**validated_data)
        return CustomSuccessResponse(
            message="Soundscape Play updated successfully.",
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


class SleepJournalEntryViewSet(viewsets.ModelViewSet):
    queryset = SleepJournalEntry.objects.all().order_by('-created_at')
    serializer_class = SleepJournalEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_paginated_response(self, data):
        return Response({
            'count': self.paginator.page.paginator.count,
            'next': self.paginator.get_next_link(),
            'previous': self.paginator.get_previous_link(),
            'status': 'success',
            'entity': data,
            'message': ''
        })

    def get_paginated_response_for_none_records(self, data):
        return Response({
            'count': 0,
            'next': None,
            'previous': None,
            'status': 'success',
            'entity': data,
            'message': 'No project records found.'
        })

    def get_queryset(self):
        return SleepJournalEntry.objects.filter(mind_space=self.request.user.mind_space_profile)
    
    def create(self, request, *args, **kwargs):
        """
        Create a new sleep journal entry.
        """
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return CustomErrorResponse(
                message=serializer.errors,
                status=400
            )
        validated_data = serializer.validated_data
        serializer.save(**validated_data)
        return CustomSuccessResponse(
            message="Sleep Journal Entry created successfully.",
            data=serializer.data
        )
        
    def update(self, request, *args, **kwargs):
        """
        Update an existing sleep journal entry.
        """
        instance = self.get_object()
        serializer = self.serializer_class(instance, data=request.data, partial=True, context={'request': request})
        if not serializer.is_valid():
            return CustomErrorResponse(
                message=serializer.errors,
                status=400
            )
        validated_data = serializer.validated_data
        serializer.save(**validated_data)
        return CustomSuccessResponse(
            message="Sleep Journal Entry updated successfully.",
            data=serializer.data
        )
        
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific sleep journal entry.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return CustomSuccessResponse(data=serializer.data)
    
    def list(self, request, *args, **kwargs):
        """
        List all sleep journal entries for the authenticated user.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return CustomSuccessResponse(data=serializer.data)


class WindDownRitualLogViewSet(viewsets.ModelViewSet):
    queryset = WindDownRitualLog.objects.all().order_by('-created_at')
    serializer_class = WindDownRitualLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WindDownRitualLog.objects.filter(mind_space=self.request.user.mind_space_profile)
    
    def create(self, request, *args, **kwargs):
        """
        Create a new wind down ritual log.
        """
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return CustomErrorResponse(
                message=serializer.errors,
                status=400
            )
        validated_data = serializer.validated_data
        serializer.save(**validated_data)
        return CustomSuccessResponse(
            message="Wind Down Ritual Log created successfully.",
            data=serializer.data
        )
        
    def update(self, request, *args, **kwargs):
        """
        Update an existing wind down ritual log.
        """
        instance = self.get_object()
        serializer = self.serializer_class(instance, data=request.data, partial=True, context={'request': request})
        if not serializer.is_valid():
            return CustomErrorResponse(
                message=serializer.errors,
                status=400
            )
        validated_data = serializer.validated_data
        serializer.save(**validated_data)
        return CustomSuccessResponse(
            message="Wind Down Ritual Log updated successfully.",
            data=serializer.data
        )
        
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific wind down ritual log.
        """ 
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return CustomSuccessResponse(data=serializer.data)
    
    def list(self, request, *args, **kwargs):
        """
        List all wind down ritual logs for the authenticated user.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return CustomSuccessResponse(data=serializer.data)