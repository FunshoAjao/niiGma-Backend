from rest_framework import serializers

class TestPushNotificationSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100)
    body = serializers.CharField()
    route = serializers.CharField(required=False, allow_blank=True)
    device_token = serializers.CharField(max_length=255, required=True)
    device_type = serializers.ChoiceField(choices=['android', 'ios', 'web'], default='android')

    def validate(self, attrs):
        if not attrs.get('device_token'):
            raise serializers.ValidationError("Registration token is required.")
        return attrs