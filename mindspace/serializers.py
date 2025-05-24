from rest_framework import serializers
from .models import MoodMirrorEntry

class MoodMirrorEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = MoodMirrorEntry
        fields = ['id', 'mood', 'reflection', 'created_at']
        read_only_fields = ['id', 'created_at']
