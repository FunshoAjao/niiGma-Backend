from rest_framework import serializers
from .models import SymptomSession, SymptomLocation, Symptom, SymptomAnalysis

class SymptomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Symptom
        fields = [
            'id', 'location', 'name', 'description', 'started_on',
            'severity', 'sensation', 'worsens_with', 'notes'
        ]


class SymptomLocationSerializer(serializers.ModelSerializer):
    symptoms = SymptomSerializer(many=True, read_only=True)

    class Meta:
        model = SymptomLocation
        fields = ['id', 'session', 'body_area', 'symptoms']


class SymptomSessionSerializer(serializers.ModelSerializer):
    locations = SymptomLocationSerializer(many=True, read_only=True)

    class Meta:
        model = SymptomSession
        fields = ['id', 'user', 'created_at', 'biological_sex', 'age', 'locations']
        read_only_fields = ['user', 'created_at']


class SymptomAnalysisSerializer(serializers.ModelSerializer):
    session = SymptomSessionSerializer(read_only=True)

    class Meta:
        model = SymptomAnalysis
        fields = ['id', 'session', 'possible_causes', 'advice', 'created_at']

class BodyPartsSerializer(serializers.Serializer):
    body_parts = serializers.ListField(required=True)
    
class BodyPartSerializer(serializers.Serializer):
    body_part = serializers.CharField(required=True)