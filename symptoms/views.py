from rest_framework import generics, viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from common.responses import CustomErrorResponse, CustomSuccessResponse
from symptoms.services.tasks import SymptomPromptBuilder, generate_and_save_analysis
from .models import FeverTriggers, SensationDescription, SymptomSession, SymptomLocation, Symptom, SymptomAnalysis
from .serializers import (
    BodyPartSerializer,
    BodyPartsSerializer,
    FeverTriggersSerializer,
    SensationDescriptionSerializer,
    SymptomSessionSerializer, 
    SymptomLocationSerializer, 
    SymptomSerializer, 
    SymptomAnalysisSerializer
)
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.db import transaction

class SensationDescriptionViewSet(viewsets.ModelViewSet):
    queryset = SensationDescription.objects.all()
    serializer_class = SensationDescriptionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_paginated_response(self, data):
        return Response({
            'status': 'success',
            'message': '',
            'data': {
                'count': self.paginator.page.paginator.count,
                'next': self.paginator.get_next_link(),
                'previous': self.paginator.get_previous_link(),
                'results': data
            }
        })

    def get_paginated_response_for_none_records(self, data):
        return Response({
            'status': 'success',
            'message': 'No record found.',
            'data': {
                'count': 0,
                'next': None,
                'previous': None,
                'results': data
            }
        })
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.get_paginated_response_for_none_records(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return CustomSuccessResponse(data=serializer.data, message="Sensation description retrieved")

class FeverTriggersViewSet(viewsets.ModelViewSet):
    queryset = FeverTriggers.objects.all()
    serializer_class = FeverTriggersSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_paginated_response(self, data):
        return Response({
            'status': 'success',
            'message': '',
            'data': {
                'count': self.paginator.page.paginator.count,
                'next': self.paginator.get_next_link(),
                'previous': self.paginator.get_previous_link(),
                'results': data
            }
        })

    def get_paginated_response_for_none_records(self, data):
        return Response({
            'status': 'success',
            'message': 'No record found.',
            'data': {
                'count': 0,
                'next': None,
                'previous': None,
                'results': data
            }
        })
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.get_paginated_response_for_none_records(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return CustomSuccessResponse(data=serializer.data, message="Fever trigger retrieved")

class SymptomSessionViewSet(viewsets.ModelViewSet):
    queryset = SymptomSession.objects.all()
    serializer_class = SymptomSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_paginated_response(self, data):
        return Response({
            'status': 'success',
            'message': '',
            'data': {
                'count': self.paginator.page.paginator.count,
                'next': self.paginator.get_next_link(),
                'previous': self.paginator.get_previous_link(),
                'results': data
            }
        })

    def get_paginated_response_for_none_records(self, data):
        return Response({
            'status': 'success',
            'message': 'No record found.',
            'data': {
                'count': 0,
                'next': None,
                'previous': None,
                'results': data
            }
        })
        
    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        Create Symptom session.
        """
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors)
       
        validated_data = serializer.validated_data
        serializer.save(user=request.user, **validated_data)
        return CustomSuccessResponse(
            message="Session created successfully.",
            data=serializer.data
        )

    def update(self, request, *args, **kwargs):
        """
        Update symptom session .
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
            message="Symptom session updated successfully.",
            data=serializer.data
        )
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.get_paginated_response_for_none_records(serializer)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return CustomSuccessResponse(data=serializer.data)


class SymptomLocationViewSet(viewsets.ModelViewSet):
    queryset = SymptomLocation.objects.all()
    serializer_class = SymptomLocationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_paginated_response(self, data):
        return Response({
            'status': 'success',
            'message': '',
            'data': {
                'count': self.paginator.page.paginator.count,
                'next': self.paginator.get_next_link(),
                'previous': self.paginator.get_previous_link(),
                'results': data
            }
        })

    def get_paginated_response_for_none_records(self, data):
        return Response({
            'status': 'success',
            'message': 'No record found.',
            'data': {
                'count': 0,
                'next': None,
                'previous': None,
                'results': data
            }
        })

    def get_queryset(self):
        return self.queryset.filter(session__user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """
        Create body location for a session.
        """
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors)
        validated_data = serializer.validated_data
        serializer.save(**validated_data)
        return CustomSuccessResponse(
            message="Body location created successfully.",
            data=serializer.data
        )

    def update(self, request, *args, **kwargs):
        """
        Update body location.
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
            message="Body location updated successfully",
            data=serializer.data
        )
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.get_paginated_response_for_none_records(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return CustomSuccessResponse(data=serializer.data)
    
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
    
    def get_paginated_response(self, data):
        return Response({
            'status': 'success',
            'message': '',
            'data': {
                'count': self.paginator.page.paginator.count,
                'next': self.paginator.get_next_link(),
                'previous': self.paginator.get_previous_link(),
                'results': data
            }
        })

    def get_paginated_response_for_none_records(self, data):
        return Response({
            'status': 'success',
            'message': 'No record found.',
            'data': {
                'count': 0,
                'next': None,
                'previous': None,
                'results': data
            }
        })

    def get_queryset(self):
        return self.queryset.filter(location__session__user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """
        Attach symptoms to a body location.
        """
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors)
        
        validated_data = serializer.validated_data
        serializer.save(**validated_data)
        return CustomSuccessResponse(
            message="Symptoms created successfully.",
            data=serializer.data
        )

    def update(self, request, *args, **kwargs):
        """
        Update symptoms.
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
            message="Symptoms updated successfully.",
            data=serializer.data
        )
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.get_paginated_response_for_none_records(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return CustomSuccessResponse(data=serializer.data)


class SymptomAnalysisView(viewsets.ModelViewSet):
    queryset = SymptomAnalysis.objects.all()
    serializer_class = SymptomAnalysisSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(session__user=self.request.user)
    
    @action(
        methods=["get"],
        detail=False,
        url_path="analyse_symptoms/(?P<id>[^/.]+)",
        permission_classes=[IsAuthenticated]
    )
    def analyse_symptoms(self, request, *args, **kwargs):
        with transaction.atomic():
            """
            Trigger AI analysis and return pre-structured result for preview.
            """
            
            symptom_id = kwargs['id']
            symptom = None
            try:
                symptom = Symptom.objects.select_related("location__session").get(id=symptom_id)
            except Symptom.DoesNotExist:
                return CustomErrorResponse(message="No symptom recorded yet!")
            builder = SymptomPromptBuilder(request.user, symptom)
            result = builder.build_analysis_from_symptoms()
            transaction.on_commit(lambda: generate_and_save_analysis.delay(symptom_id))
            return CustomSuccessResponse(data=result, message="Symptoms analyzed successfully")
    
    @action(
        methods=["get"],
        detail=False,
        url_path="timeline",
        permission_classes=[IsAuthenticated]
    )
    def timeline(self, request):
        """
        Return a summary of all symptom sessions for the user.
        """
        sessions = SymptomSession.objects.prefetch_related("locations__symptoms", "analysis").filter(user=request.user)
        timeline = []

        timeline = [
            {
                "title": symptom.symptom_names[0] if symptom.symptom_names else "Symptom",
                "date": session.created_at.strftime("%Y-%m-%d"),
                "type": "Report" if hasattr(session, "analysis") else "Symptom",
                "session_id": session.id,
                "symptom_id": symptom.id,
            }
            for session in sessions
            for location in session.locations.all()
            for symptom in location.symptoms.all()
        ]

        return CustomSuccessResponse(data=timeline)

    @action(
        methods=["get"],
        detail=False,
        url_path="symptom-detail/(?P<symptom_id>[^/.]+)",
        permission_classes=[IsAuthenticated]
    )
    def symptom_detail(self, request, symptom_id=None):
        """
        Return tracked details for a single symptom.
        """
        try:
            symptom = Symptom.objects.select_related("location__session").get(id=symptom_id)
        except Symptom.DoesNotExist:
            return CustomErrorResponse(message="Symptom not found!")

        return CustomSuccessResponse(data={
            "recorded_at": symptom.created_at.strftime("%Y-%m-%d %H:%M"),
            "body_area": symptom.location.body_area,
            "symptom_names": symptom.symptom_names,
        })

    @action(
        methods=["get"],
        detail=False,
        url_path="report-detail/(?P<session_id>[^/.]+)",
        permission_classes=[IsAuthenticated]
    )
    def report_detail(self, request, session_id=None):
        """
        Return detailed AI health report for a specific session.
        """
        try:
            session = SymptomSession.objects.prefetch_related("locations__symptoms", "analysis").get(id=session_id, user=request.user)
            analysis = session.analysis
            first_symptom = session.locations.first().symptoms.first()
        except (SymptomSession.DoesNotExist, AttributeError):
            return CustomErrorResponse(message="Report not found or incomplete.")

        return CustomSuccessResponse(data={
            "recorded_at": session.created_at.strftime("%Y-%m-%d %H:%M"),
            "age_sex": f"{session.age}yrs {session.biological_sex}",
            "conditions": [cause["name"] for cause in analysis.possible_causes],
            "duration": "1 week",  # Optional: make dynamic if you wish
            "area": first_symptom.location.body_area if first_symptom else "N/A",
            "full_details": {
                "summary": f"Reported Symptoms: {', '.join(first_symptom.symptom_names)}" if first_symptom else "",
                "causes": analysis.possible_causes,
                "advice": analysis.advice,
            }
        })