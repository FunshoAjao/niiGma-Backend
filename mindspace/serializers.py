from rest_framework import serializers

from mindspace.choices import MindSpaceFrequencyType
from .models import MindSpaceProfile, MoodMirrorEntry

class MoodMirrorEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = MoodMirrorEntry
        fields = ['id', 'mood', 'reflection', 'created_at', 'date']
        read_only_fields = ['id', 'created_at']
        
class MindSpaceProfileSerializer(serializers.ModelSerializer):
    frequency_type = serializers.ChoiceField(choices=MindSpaceFrequencyType, default='Daily')
    goals = serializers.ListField(
        child=serializers.CharField(max_length=255),
        default=list,
        allow_empty=True
    )
    
    def validate_frequency_type(self, value):
        if value not in MindSpaceFrequencyType.values:
            raise serializers.ValidationError("Invalid frequency type.")
        return value
    
    def validate_goals(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Goals must be a list.")
        return value
    
    class Meta:
        model = MindSpaceProfile
        fields = ['id', 'frequency_type', 'goals']
        read_only_fields = ['id']
        extra_kwargs = {
            'frequency_type': {'required': True},
            'goals': {'required': True}
        }
