from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=True)
    email = serializers.EmailField(required=True, validators=[])

    class Meta:
        model = User
        fields = [
            "id", "email", "password", "first_name", "last_name",
            "goals", "date_of_birth", "height", "wellness_status", "referral_source",
            "is_active", "last_login", "is_superuser", "is_staff",
            "account_verified", "account_verified_at", "created_at", "updated_at"
        ]
        read_only_fields = [
            "account_verified", "account_verified_at", "is_active",
            "last_login", "is_superuser", "is_staff", "created_at", "updated_at"
        ]

    def validate_email(self, value):
        value = value.strip().lower()
        if not value:
            raise serializers.ValidationError("Email field cannot be empty.")
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

