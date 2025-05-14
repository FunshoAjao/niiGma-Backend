from django.shortcuts import render
from accounts.choices import Section
from calories.services.tasks import handle_calorie_ai_interaction
from common.responses import CustomErrorResponse, CustomSuccessResponse
from rest_framework.views import status, APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import viewsets
from .models import *
from .serializers import CalorieAISerializer, CalorieSerializer
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.decorators import action
import logging

logger = logging.getLogger(__name__)

class CalorieViewSet(viewsets.ModelViewSet):
    queryset = CalorieQA.objects.all().order_by('-created_at')
    serializer_class = CalorieSerializer
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
            'message': 'No records found.'
        })

    def create(self, request, *args, **kwargs):
        """Create or update the user's calorie object (only one entry per user)"""
        data = request.data.copy()
        data.pop('user', None) 
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors, status=400)

        validated_data = serializer.validated_data
        obj, created = CalorieQA.objects.update_or_create(
            user=request.user,
            defaults=validated_data
        )

        response_serializer = self.get_serializer(obj)
        message = "Calorie created successfully" if created else "Calorie updated successfully"
        return CustomSuccessResponse(data=response_serializer.data, message=message, status=201 if created else 200)


    def list(self, request, *args, **kwargs):
        """Get calories created"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return CustomSuccessResponse(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """Get a single object"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return CustomSuccessResponse(data=serializer.data)

    def update(self, request, *args, **kwargs):
        """update an instance"""
        partial = kwargs.pop('partial', False)
        
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors, status=400)
        
        instance.save()
        
        return CustomSuccessResponse(data=serializer.data, message="User updated successfully")

    def destroy(self, request, *args, **kwargs):
        """Delete instance"""
        instance = self.get_object()
        self.perform_destroy(instance)
        return CustomSuccessResponse(message="Calorie deleted successfully")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    @action(
        methods=["post"],
        detail=False,
        url_path="ai_prompt",
        permission_classes=[IsAuthenticated],
        serializer_class = CalorieAISerializer
    )
    def ai_prompt(self, request, *args, **kwargs):
        logger.info("Ai about to be triggered")
        
        serializer = CalorieAISerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Validation error occurred: {serializer.errors}")
            return CustomErrorResponse(message=serializer.errors, status=400)

        validated_data = serializer.validated_data
        user_prompt = validated_data.get("prompt")

        ai_response = handle_calorie_ai_interaction(request.user, Section.CALORIES, user_prompt)
        logger.info('Prompt and response generated for calorie successfully!')

        return CustomSuccessResponse(data=ai_response, message="Conversation loaded successfully!", status=201)
