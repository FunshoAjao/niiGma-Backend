from rest_framework import generics, viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from common.responses import CustomErrorResponse, CustomSuccessResponse
from symptoms.services.tasks import SymptomPromptBuilder
from .models import SymptomSession, SymptomLocation, Symptom, SymptomAnalysis
from .serializers import (
    BodyPartSerializer,
    BodyPartsSerializer,
    SymptomSessionSerializer, 
    SymptomLocationSerializer, 
    SymptomSerializer, 
    SymptomAnalysisSerializer
)

class SymptomSessionViewSet(viewsets.ModelViewSet):
    queryset = SymptomSession.objects.all()
    serializer_class = SymptomSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SymptomLocationViewSet(viewsets.ModelViewSet):
    queryset = SymptomLocation.objects.all()
    serializer_class = SymptomLocationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(session__user=self.request.user)
    
    @action(
        methods=["post"],
        detail=False,
        url_path="symptoms_by_body_parts",
        permission_classes=[IsAuthenticated],
        serializer_class=BodyPartsSerializer
    )
    def symptoms_by_body_parts(self, request, *args, **kwargs):
        """
        Generate list of symptoms by body parts.
        """
        user = request.user
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors)
        
        symptoms = SymptomPromptBuilder(
            user
        ).build_by_multiple_body_parts(
            serializer.validated_data['body_parts']
        )
            
        return CustomSuccessResponse(data=symptoms, message="Symptoms generated successfully")
    
    @action(
        methods=["post"],
        detail=False,
        url_path="symptoms_by_body_part",
        permission_classes=[IsAuthenticated],
        serializer_class=BodyPartSerializer
    )
    def symptoms_by_body_part(self, request, *args, **kwargs):
        """
        Generate list of symptoms by body parts.
        """
        user = request.user
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors)
        
        symptoms = SymptomPromptBuilder(
            user
        ).build_by_body_part(
            serializer.validated_data['body_part']
        )
            
        return CustomSuccessResponse(data=symptoms, message="Symptoms generated successfully")


class SymptomViewSet(viewsets.ModelViewSet):
    queryset = Symptom.objects.all()
    serializer_class = SymptomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(location__session__user=self.request.user)


class SymptomAnalysisView(generics.RetrieveAPIView):
    queryset = SymptomAnalysis.objects.all()
    serializer_class = SymptomAnalysisSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(session__user=self.request.user)
