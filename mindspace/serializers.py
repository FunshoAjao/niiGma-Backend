from rest_framework import serializers

from mindspace.choices import MindSpaceFrequencyType
from .models import *

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
        
class SoundscapeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SoundscapeLibrary
        fields = ['id', 'name', 'description', 'audio_url', 'duration', 'mood_tag']


class SoundscapePlaySerializer(serializers.ModelSerializer):
    soundscape = SoundscapeSerializer(read_only=True)
    class Meta:
        model = SoundscapePlay
        fields = '__all__'
        read_only_fields = ['id', 'started_at', 'mind_space']

    def create(self, validated_data):
        validated_data['mind_space'] = self.context['request'].user.mind_space_profile
        return super().create(validated_data)


class SleepJournalEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = SleepJournalEntry
        fields = '__all__'
        read_only_fields = ['id', 'mind_space']

    def create(self, validated_data):
        validated_data['mind_space'] = self.context['request'].user.mind_space_profile
        return super().create(validated_data)


class WindDownRitualLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WindDownRitualLog
        fields = ['id', 'ritual_type', 'entries', 'reflection', 'metadata', 'completed_at']
        read_only_fields = ['id', 'completed_at', 'mind_space']

    def create(self, validated_data):
        validated_data['mind_space'] = self.context['request'].user.mind_space_profile
        return super().create(validated_data)