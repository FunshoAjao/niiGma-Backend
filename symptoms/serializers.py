from rest_framework import serializers
from .models import FeverTriggers, SensationDescription, SymptomSession, SymptomLocation, Symptom, SymptomAnalysis

class SymptomSerializer(serializers.ModelSerializer):
    symptom_names = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False
    )
    body_areas = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False
    )

    class Meta:
        model = Symptom
        fields = [
            'id', 'body_areas', 'symptom_names', 'description', 'session',
            'started_on', 'severity', 'sensation', 'worsens_with', 'notes', 'created_at'
        ]
        read_only_fields = ['created_at']


class SymptomLocationSerializer(serializers.ModelSerializer):
    symptoms = SymptomSerializer(many=True, read_only=True)

    class Meta:
        model = SymptomLocation
        fields = ['id', 'session', 'body_area', 'symptoms', 'created_at']
        read_only_fields = ['created_at']


class SymptomSessionSerializer(serializers.ModelSerializer):
    symptoms = SymptomSerializer(many=True, read_only=True)

    class Meta:
        model = SymptomSession
        fields = ['id', 'user', 'biological_sex', 'age', 'symptoms', 'created_at']
        read_only_fields = ['user', 'created_at']


class SymptomAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = SymptomAnalysis
        fields = ['id', 'session', 'possible_causes', 'advice', 'created_at']
        read_only_fields = ['created_at']

class BodyPartsSerializer(serializers.Serializer):
    body_parts = serializers.ListField(required=True)
    
class BodyPartSerializer(serializers.Serializer):
    body_part = serializers.CharField(required=True)
    
class SensationDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensationDescription
        fields = "__all__"

class FeverTriggersSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeverTriggers
        fields = "__all__"