from rest_framework import serializers
from .models import CycleInsight, CycleSetup, OvulationLog

class OvulationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = OvulationLog
        fields = [
            "id", "date", "flow", "symptoms", "mood", "sex_purpose",
            "notes", "discharge", "sexual_activity"
        ]

class CycleSetupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CycleSetup
        fields = [
            "id",
            "user",
            "cycle_length",
            "period_length",
            "first_period_date",
            "current_focus",
            "regularity",
            "created_at",
            "updated_at"
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def update(self, instance, validated_data):
        # Optional: add any business logic for update (e.g., triggering recalculations)
        return super().update(instance, validated_data)

class CycleOnboardingSetUpSerializer(serializers.Serializer):
    step = serializers.CharField(required=True)
    answer = serializers.CharField(required=True, allow_blank=False)
    
class CycleStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CycleInsight
        fields = [
            "id",
            "user",
            "date",
            "day_in_cycle",
            "phase",
            "days_to_next_phase",
            "average_cycle_length",
            "average_period_length",
            "regularity",
            "total_months_tracked"
        ]
        read_only_fields = ["id", "user", "date"]

    
class CycleInsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = CycleInsight
        fields = [
            "id",
            "date",
            "phase",
            "confidence",
            "headline",
            "detail"
        ]
        
class InsightBlockSerializer(serializers.Serializer):
    headline = serializers.CharField()
    detail = serializers.CharField()
    confidence = serializers.CharField()
