from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.generics import ListAPIView
from django.middleware.csrf import get_token
from django.utils import timezone
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.permissions import AllowAny
from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from rest_framework.decorators import action
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.cache import cache
from accounts.choices import Section
from accounts.services.tasks import send_otp
from calories.models import CalorieQA
from calories.serializers import CalorieSerializer
from calories.services.tasks import CalorieAIAssistant
from ovulations.services.tasks import calculate_cycle_state
from reminders.services.tasks import send_push_notification
from utils.helpers.services import generate_otp
from rest_framework_simplejwt.authentication import JWTAuthentication
from .services.user import UserService
from common.responses import CustomErrorResponse, CustomSuccessResponse
from rest_framework.response import Response
from rest_framework.views import status, APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import PromptHistory, User
from .serializers import AccountPasswordResetSerializer, ChangePasswordSerializer, ChatWithAiSerializer, DeviceTokenSerializer, EmailSerializer, LoginSerializer, LogoutSerializer, PasswordResetConfirmationSerializer, PromptHistorySerializer, PushNotificationSerializer, UserSerializer, VerificationCodeSerializer
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-created_at')
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

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
            'message': 'No user records found.',
            'data': {
                'count': 0,
                'next': None,
                'previous': None,
                'results': data
            }
        })


    def create(self, request, *args, **kwargs):
        raise NotFound()

    def list(self, request, *args, **kwargs):
        """Get users created"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return CustomSuccessResponse(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """Get a user"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return CustomSuccessResponse(data=serializer.data)

    def update(self, request, *args, **kwargs):
        """update user"""
        partial = kwargs.pop('partial', False)
        request.data.pop('password', None)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors, status=400)
        
        try:
            self.perform_update(serializer)
            instance.refresh_from_db()
            required_fields = [
                instance.date_of_birth,
                instance.height,
                instance.wellness_status,
                instance.referral_source,
                instance.goals
            ]

            # Check if all required fields are filled
            if all(required_fields) and not instance.has_completed_onboarding:
                instance.has_completed_onboarding = True
                instance.onboarding_completed_at = timezone.now()
                instance.save(update_fields=['has_completed_onboarding', 'onboarding_completed_at'])
                return CustomSuccessResponse(data=serializer.data, message="User updated successfully")
            
            return CustomSuccessResponse(data=serializer.data, message="User updated successfully")
        except Exception as e:
            return CustomErrorResponse(message=str(e))

    def destroy(self, request, *args, **kwargs):
        """Delete user"""
        instance = self.get_object()
        self.perform_destroy(instance)
        return CustomSuccessResponse(message="User deleted successfully")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    @action(
        methods=["post"],
        detail=False,
        url_path="account_verification",
        permission_classes=[AllowAny],
        authentication_classes = [],
        serializer_class=VerificationCodeSerializer
    )
    def account_verification(self, request, *args, **kwargs):
        logger.info(f"Account verification request received: {request.data}")

        serializer = VerificationCodeSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Validation error in account verification: {serializer.errors}")
            return CustomErrorResponse(message=serializer.errors, status=400)

        validated_data = serializer.validated_data
        email = validated_data.get("email")
        verification_code = validated_data.get("verification_code")

        user_service = UserService(user=request.user)
        user, token = user_service.verify_user(verification_code, email)
        logger.info(f"User {email} verified successfully")

        data = {
            "access": token.get("access"),
            "refresh": token.get("refresh"),
            "customer": UserSerializer(user).data
        }
        return CustomSuccessResponse(data=data, message="Account Verified successfully", status=201)

    @action(
        methods=["post"],
        detail=False,
        url_path="create",
        permission_classes=[AllowAny],
        authentication_classes=[],
        serializer_class=UserSerializer
    )
    def user_create(self, request, *args, **kwargs):
        with transaction.atomic():
            try:
                serializer = UserSerializer(data=request.data)
                if not serializer.is_valid():
                    return CustomErrorResponse(message=serializer.errors, status=400)

                validated_data = serializer.validated_data

                user_service = UserService()
                user, token = user_service.create_user(**validated_data)

                data = {
                    "access": token.get("access"),
                    "refresh": token.get("refresh"),
                    "customer": self.serializer_class(user).data
                }
                return CustomSuccessResponse(data=data, message="User created successfully", status=201)

            except Exception as e:
                return CustomErrorResponse(message=str(e), status=500)


    @action(
        methods=["post"],
        detail=False,
        url_path="login",
        permission_classes=[AllowAny],
        authentication_classes = [],
        serializer_class=LoginSerializer
    )
    def login(self, request, *args, **kwargs):
        logger.info(f"Login request received with data: {request.data}")
        
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Login validation failed: {serializer.errors}")
            return CustomErrorResponse(message=serializer.errors, status=400)

        validated_data = serializer.validated_data
        logger.info(f"Validated login data: {validated_data}")
        
        user_service = UserService()
        try:
            user, token = user_service.login(validated_data.get('email'), validated_data.get('password'))
            logger.info(f"Login successful for user: {user.email}")
        except serializers.ValidationError as e:
            logger.error(f"Login validation error: {str(e)}")
            return Response(e.detail, status=400)
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
            return Response({"message": "An unexpected error occurred"}, status=500)

        data = {
            "access": token.get("access"),
            "refresh": token.get("refresh"),
            "customer": UserSerializer(user).data
        }
        logger.info("Login completed successfully")
        setup = getattr(user, "cycle_setup_records", None)
        if setup and getattr(setup, "setup_complete", False):
            calculate_cycle_state.delay(user.id, timezone.now().date())
            logger.info(f"Cycle state updated for user: {user.email}")
        return CustomSuccessResponse(data=data, message='Logged in successfully')

    @action(
        methods=["post"],
        detail=False,
        url_path="update_device_token",
        permission_classes=[IsAuthenticated],
        serializer_class=DeviceTokenSerializer
    )
    def update_device_token(self, request, *args, **kwargs):
        with transaction.atomic():
            data = request.data
            serializer = DeviceTokenSerializer(data=data)
            if not serializer.is_valid():
                return CustomErrorResponse(message=serializer.errors, status=400)
            validated_data = serializer.validated_data
            user_service = UserService(user=request.user)
            user, token = user_service.update_device_token(
                validated_data['device_token'], validated_data['device_type'], request.user.email
            )

            data = {
                "access": token.get("access"),
                "refresh": token.get("refresh"),
                "transporter": UserSerializer(user).data
            }
            return CustomSuccessResponse(data=data, message="Device token updated successfully", status=201)

    @action(
    methods=["post"],
    detail=False,
    url_path="test_push_notification",
    serializer_class=PushNotificationSerializer,
    permission_classes=[IsAuthenticated],
    )
    def test_push_notification(self, request, *args, **kwargs):
        try:
            user= request.user
            serializer = PushNotificationSerializer(data=request.data)
            if not serializer.is_valid():
                return CustomErrorResponse(message=serializer.errors, status=400)
            validated_data = serializer.validated_data
            if not user.device_token or not user.device_type:
                return CustomErrorResponse(message="Device token or type not found", status=400)
            title = validated_data.get("title")
            body = validated_data.get("body")
            
            send_push_notification(
                title=title,
                message=body,
                device_type=user.device_type,
                registration_token=user.device_token
            )
            return CustomSuccessResponse(message="", status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            logger.error(f"Error sending push notification: {str(e)}")  
            return CustomErrorResponse(message=e.args[0])

    @action(
    methods=["post"],
    detail=False,
    url_path="logout",
    serializer_class = LogoutSerializer,
    permission_classes=[IsAuthenticated]
    )
    def logout(self, request, *args, **kwargs):
        try:
            refresh_token = request.data["refresh_token"]
            user_service = UserService()
            user_service.logout(refresh_token)
            
            return CustomSuccessResponse(message="Logged out successfully!", status=status.HTTP_408_REQUEST_TIMEOUT)
        except Exception as e:
            return CustomErrorResponse(message=e.args[0])

    @action(
        methods=["get"],
        detail=False,
        url_path="get_user",
        permission_classes=[IsAuthenticated],
        authentication_classes=[JWTAuthentication]
    )
    def get_user(self, request, *args, **kwargs):
        try:
            user = request.user

            return CustomSuccessResponse(data={
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_active": user.is_active,
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                    "is_superuser": user.is_superuser,
                    "is_staff": user.is_staff,
                    "age": user.age,
                    "gender":user.gender,
                    "profile_picture": user.profile_picture,
                    "account_verified": user.account_verified,
                    "account_verified_at": user.account_verified_at.isoformat() if user.account_verified_at else None,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                    "avatar_url": user.avatar_url if hasattr(user, "avatar_url") else None,
                    "has_completed_onboarding": user.has_completed_onboarding,
                    "is_calories_setup": user.is_calories_setup,
                    "is_mind_space_setup":user.is_mind_space_setup,
                    "is_ovulation_tracker_setup":user.is_ovulation_tracker_setup,
                    "is_trivia_setup":user.is_trivia_setup,
                    "onboarding_completed_at": user.onboarding_completed_at.isoformat() if user.onboarding_completed_at else None,
                    "calories_profile": CalorieSerializer(user.calorie_qa).data if hasattr(user, 'calorie_qa') else None,
                    "user_current_calorie_streak": user.calorie_streak.current_streak if hasattr(user, "calorie_streak") else None,
                    "user_longest_calorie_streak": user.calorie_streak.longest_streak if hasattr(user, "calorie_streak") else None,
                })
        except Exception as e:
            return CustomErrorResponse(message="Failed to retrieve user information", status=500)

    @action(
        methods=["post"],
        detail=False,
        url_path="resend_account_verification",
        permission_classes=[AllowAny],
        authentication_classes = [],
        serializer_class=EmailSerializer
    )
    def resend_account_verification(self, request, *args, **kwargs):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        user_service = UserService()
        user_service.resend_account_verification(validated_data['email'])
        return CustomSuccessResponse(message="verification code sent")

    @action(
        methods=["post"],
        detail=False,
        url_path="change_password",
        permission_classes=[IsAuthenticated],
        serializer_class=ChangePasswordSerializer
    )
    def change_password(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors, status=400)
        validated_data = serializer.validated_data
        customer = User.objects.get(user=request.user)
        user_service = UserService(customer=customer)
        user_service.change_password(
            old_password=validated_data.get("old_password"),
            new_password=validated_data.get("new_password")
        )

        return CustomSuccessResponse(message="Password changed successfully", status=200)

    @action(
        methods=["post"],
        detail=False,
        url_path="initiate_password_reset",
        permission_classes=[AllowAny],
        authentication_classes = [],
        serializer_class=EmailSerializer
    )
    def initiate_password_reset(self, request, *args, **kwargs):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        user_service = UserService()
        user_service.password_reset(
            email=validated_data.get("email")
        )
        return CustomSuccessResponse(message="password reset verification code sent",)

    @action(
        methods=["post"],
        detail=False,
        url_path="confirm_password",
        permission_classes=[AllowAny],
        authentication_classes = [],
        serializer_class=PasswordResetConfirmationSerializer
    )
    def confirm_password(self, request, *args, **kwargs):
        with transaction.atomic():
            serializer = PasswordResetConfirmationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            validated_data = serializer.validated_data
            user_service = UserService()
            user, token = user_service.password_reset_confirmation(
                validated_data.get("verification_code"),
                validated_data.get("password"),
            )
            data = {
                "access": token.get("access"),
                "refresh": token.get("refresh"),
                "customer": UserSerializer(user).data
            }
            return CustomSuccessResponse(data=data, message='Password reset successfully')

    @action(
        methods=["post"],
        detail=False,
        url_path="reset_password",
        authentication_classes = [],
        serializer_class=AccountPasswordResetSerializer
    )
    def reset_password(self, request, *args, **kwargs):
        serializer = AccountPasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors, status=400)
        validated_data = serializer.validated_data
        user_service = UserService()
        user, token = user_service.reset_account_password(
            email=validated_data.get("email"),
            password=validated_data['password'],
            verification_code=validated_data['verification_code']
        )
        data = {
                "access": token.get("access"),
                "refresh": token.get("refresh"),
                "back_office": UserSerializer(user).data
            }
        return CustomSuccessResponse(data=data, message='Password reset successfully')

    @action(
        methods=["post"],
        detail=False,
        url_path="resend_otp",
        authentication_classes = [],
        serializer_class=EmailSerializer
    )
    def resend_otp(self, request, *args, **kwargs):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors, status=400)
        
        if not User.objects.filter(email=serializer.validated_data['email']).exists():
            return CustomErrorResponse(message="User with this email does not exist", status=404)

        otp = generate_otp()
        cache.set(serializer.validated_data['email'], otp)

        send_otp.delay(serializer.validated_data['email'], otp)

        return CustomSuccessResponse(message = "Otp has been sent to your mail.")

    @action(
        methods=["post"],
        detail=False,
        url_path="refresh_token",
        permission_classes=[AllowAny],
    )
    def refresh_token(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return CustomErrorResponse(
                    message="Refresh token is required",
                    status=400
                )

            token = RefreshToken(refresh_token)
            new_access_token = str(token.access_token)

            return CustomSuccessResponse(
                data={"access": new_access_token},
                message="Token refreshed successfully"
            )
        except TokenError as e:
            return CustomErrorResponse(
                message="Invalid refresh token",
                status=401
            )
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            return CustomErrorResponse(
                message="Failed to refresh token",
                status=500
            )
            
    @action(
        methods=["post"],
        detail=False,
        url_path="chat_with_ai",
        permission_classes=[IsAuthenticated],
        serializer_class=ChatWithAiSerializer
    )
    def chat_with_ai(self, request, *args, **kwargs):
        user = request.user
        serializer = ChatWithAiSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors, status=400)
        validated_data = serializer.validated_data
        response, conversation_id = CalorieAIAssistant(user).chat_with_ai(
            validated_data.get("user_prompt"),
            validated_data.get("conversation_id", None),
            validated_data.get("base_64_image"),
            validated_data.get("text")
        )
        return CustomSuccessResponse(data={'response':response, 'conversation_id':conversation_id}, message="Chat with AI initiated successfully")
    
    
            
class PromptHistoryView(viewsets.ModelViewSet):
    queryset = PromptHistory.objects.all()
    serializer_class = PromptHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        section = self.request.query_params.get("section")
        print(f"Section filter: {section}")
        if section is None:
            section = Section.NONE
        queryset = PromptHistory.objects.filter(user=self.request.user)
        if section:
            queryset = queryset.filter(section=section)
        return queryset
    
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
        
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="section",
                description="Filter by section",
                required=False,
                type=str,
                enum=[section.value for section in Section]
            ),
            OpenApiParameter(
                name="page_size",
                description="Page number for pagination",   
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="page",
                description="Page size for pagination",
                required=False,
                type=int,
            )
        ]
    )
    @action(
        detail=False, methods=["get"],
        url_path="conversation/(?P<conversation_id>[^/.]+)",
        serializer_class=PromptHistorySerializer,
        permission_classes=[IsAuthenticated]
        )
    def get_conversation(self, request, conversation_id):
        queryset = PromptHistory.objects.filter(user=request.user, conversation_id=conversation_id)
        section = request.query_params.get("section")
        if section:
            queryset = queryset.filter(section=section)
        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response_for_none_records(data=serializer.data)