import base64
import uuid
import requests
from rest_framework import serializers

from django.core.files.base import ContentFile
from accounts.choices import DeviceType, Gender
from utils.helpers.cloudinary import CloudinaryFileUpload
from .models import Conversation, PromptHistory, User

class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        user_id = self.context['request'].user.id
        data = self.sanitize_base64_image(data)

        if isinstance(data, str) and data.startswith('data:image'):
            mime_type, imgstr = data.split(';base64,')
            ext = mime_type.split('/')[-1]
            img_data = ContentFile(base64.b64decode(imgstr), name=f"{uuid.uuid4()}.{ext}")
            file_name = f"{user_id}"
            
            # ✅ Upload to Cloudinary
            uploaded_file = CloudinaryFileUpload().upload_file_to_cloudinary_v1(img_data, file_name)
            
            return uploaded_file
        
        # 🟢 If it's a remote URL
        elif isinstance(data, str) and data.startswith("http"):
            response = requests.get(data)
            if response.status_code != 200:
                raise serializers.ValidationError("Failed to download image from URL")
            ext = data.split(".")[-1].split("?")[0]
            file_name = f"{user_id}.{ext}"
            img_data = ContentFile(response.content, name=file_name)
            return CloudinaryFileUpload().upload_file_to_cloudinary_v1(img_data, file_name)

        return super().to_internal_value(data)

    def sanitize_base64_image(self, data):
        if data.startswith("data:@file/jpeg;base64"):
            return data.replace("data:@file/jpeg;base64", "data:image/jpeg;base64")
        return data
    
    def to_representation(self, value):
        return str(value) if value else None

class UserSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    goals = serializers.JSONField(required=False)
    date_of_birth = serializers.DateTimeField(required=False)
    height = serializers.FloatField(required=False)
    height_unit = serializers.ChoiceField(required=False, choices=["cm", "inches", "ft"])
    gender = serializers.ChoiceField(required=False, choices=Gender)
    referral_source = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=True)
    email = serializers.EmailField(required=True, validators=[])
    profile_picture = Base64ImageField(required=False)

    class Meta:
        model = User
        fields = [
            "id", "email", "password", "first_name", "last_name",
            "goals", "date_of_birth", "height", "height_unit", "wellness_status", "referral_source", "allow_push_notifications", "allow_ovulation_tracker", 
            "is_active", "last_login", "is_superuser", "is_staff", "profile_picture", "gender",
            "account_verified", "account_verified_at", "created_at", "updated_at", "has_completed_onboarding", "is_calories_setup", "is_mind_space_setup", "is_ovulation_tracker_setup", "is_trivia_setup", "country",
        ]
        read_only_fields = [
            "account_verified", "account_verified_at", "is_active",
            "last_login", "is_superuser", "is_staff", "created_at", "updated_at", "has_completed_onboarding", "is_calories_setup", "is_mind_space_setup", "is_ovulation_tracker_setup", "is_trivia_setup"
        ]

    def validate_email(self, value):
        value = value.strip().lower()
        if not value:
            raise serializers.ValidationError("Email field cannot be empty.")
        if not self.instance and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def update(self, instance, validated_data):
        # profile_picture is already handled by Base64ImageField
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If updating (instance exists), make email read-only
        if self.instance:
            self.fields['password'].read_only = True
            self.fields['email'].read_only = True

class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255, required=True)

    def to_internal_value(self, data):
        """Ensures email is always stored in lowercase."""
        data = super().to_internal_value(data)
        data["email"] = data["email"].lower()
        return data


class AccountPasswordResetSerializer(EmailSerializer):
    password = serializers.CharField(required=True)
    verification_code = serializers.RegexField(
        regex=r'^\d{6}$',
        required=True,
        error_messages={
            "invalid": "This field must contain exactly 6 digits."
        }
    )

class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class LoginSerializer(EmailSerializer):
    email = serializers.EmailField(max_length=255, required=True)
    password = serializers.CharField(required=True)

class VerificationCodeSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)
    verification_code = serializers.RegexField(
        regex=r'^\d{6}$',
        required=True,
        error_messages={
            "invalid": "This field must contain exactly 6 digits."
        }
    )

    def validate_verification_code(self, value):
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate(self, data):
        old_password = data.get("old_password")
        new_password = data.get("new_password")

        if old_password == new_password:
            raise serializers.ValidationError(
                {"message": "Password could not be changed, Password has previously been used. Try another password"
                 , "status":"failed"},
                code=400
            )

        return data

class PasswordResetConfirmationSerializer(VerificationCodeSerializer):
    password = serializers.CharField(required=True)


class PromptHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptHistory
        fields = '__all__'
        
class ChatWithAiSerializer(serializers.Serializer):
    user_prompt = serializers.CharField(required=True)
    base_64_image = serializers.CharField(required=False, allow_blank=True)
    text = serializers.CharField(required=False, allow_blank=True)
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
    
class PushNotificationSerializer(serializers.Serializer):
    title = serializers.CharField(required=True)
    message = serializers.CharField(required=True)
    

class DeviceTokenSerializer(serializers.Serializer):
    device_token = serializers.CharField(required=True)
    device_type = serializers.ChoiceField(choices=DeviceType, required=True)
    
class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']