from rest_framework import generics, viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import SymptomSession, SymptomLocation, Symptom, SymptomAnalysis
from .serializers import (
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
