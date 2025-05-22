from accounts.choices import *
from ..models import User
from django.db.utils import IntegrityError
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from django.conf import settings
from .tasks import  send_account_verification_email, send_sign_up_email, verify_account_email, send_reset_request_mail
from utils.helpers.services import generate_otp
from django.core.exceptions import ObjectDoesNotExist
from decouple import config
import logging
logger = logging.getLogger(__name__)

class UserService:
    _settings_config = None

    def __init__(self, user=None) -> None:
        self.user = user
    def __get_tokens_for_user(self):
        refresh=RefreshToken.for_user(self.user)
        last_login = timezone.now() + timezone.timedelta(hours=1)
        self.user.last_login = last_login
        self.user.save()

        refresh['first_name']=self.user.first_name
        refresh['email']=self.user.email

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
        
    @transaction.atomic
    def update_device_token(self, device_token, device_type, email):
        try:
            self.user = User.objects.get(email=email)
            
        except ObjectDoesNotExist:
            raise serializers.ValidationError(
                {"message": "User does not exist", "status":"failed"},
                code=400
            )
        self.user.device_token = device_token
        self.user.device_type = device_type
        self.user.save()
        
        return self.user, self.__get_tokens_for_user()

    @transaction.atomic
    def create_user(self, **kwargs):
        return self.__create_user(**kwargs)

    @transaction.atomic
    def __create_user(self, **kwargs):
        try:
            email = kwargs.pop('email')
            password = kwargs.pop('password')
            first_name = kwargs.pop("first_name")
            last_name = kwargs.pop("last_name")

            if not User.objects.filter(email=email).exists():
                self.user = User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=False,
                    account_verified=False,
                    account_verified_at=None,
                    **kwargs
                )
                self.user.set_password(password)
                self.user.save()

            else:
                raise serializers.ValidationError({"message": f"This user already exists '{email}'", "status":"failed"})

            logger.info(f"Generating OTP for user: {email}")
            verification_code = generate_otp()
            cache.set(email, verification_code)
            logger.info(f"OTP cached for user: {email} — Code: {verification_code}")

            logger.info(f"About to queue sign_up_email task for user: {email}")
            transaction.on_commit(lambda: send_sign_up_email.delay(email, verification_code))
            logger.info(f"sign_up_email task successfully queued for: {email}")

            self.user.refresh_from_db()
            token = self.__get_tokens_for_user()
            return self.user, token

        except Exception as error:
            logger.error(f"Error creating user: {error}")
            raise serializers.ValidationError(
                {"message": str(error), "status":"failed"},
                code=400
            )

    @transaction.atomic
    def verify_user(self, verification_code, email):
        logger.info(f"Verifying user with email: {email}")
        try:
            # Convert email to lowercase for case-insensitive matching
            email = email.lower().strip()
            logger.info(f"Looking for user with normalized email: {email}")

            # Use case-insensitive query
            self.user = User.objects.get(email__iexact=email)
            logger.info(f"User found in database: {self.user.email}")
        except ObjectDoesNotExist:
            logger.error(f"User not found in database: {email}")
            raise serializers.ValidationError(
                {"message": "User does not exist", "status":"failed"},
                code=400
            )

        cached_code = cache.get(email)
        logger.info(f"Cached verification code for {email}: {cached_code}")

        if cached_code is not None:
            verification_status = int(cached_code) == int(verification_code)
            logger.info(f"Verification status for {email}: {verification_status}")

            if verification_status:
                logger.info(f"Verification successful for {email}")
                self.user.is_active = True
                self.user.account_verified = True
                self.user.account_verified_at = timezone.now()
                self.user.save()
                cache.delete(email)
                logger.info(f"User {email} activated and verified")

                transaction.on_commit(lambda: send_account_verification_email.delay(email))
                logger.info(f"Verification email sent to {email}")

                return self.user, self.__get_tokens_for_user()

        logger.error(f"Invalid or expired verification code for {email}")
        raise serializers.ValidationError(
                {"message": "Invalid or expired verification code", "status":"failed"},
                code=400
            )

    def login(self, email, password):
        logger.info(f"Attempting login for email: {email}")

        try:
            if User.objects.filter(email=email).exists():
                self.user = User.objects.get(email=email)
                logger.info(f"User found: {self.user.email}")

                if not self.user.is_active:
                    logger.warning(f"User {email} is not active")
                    verification_code = generate_otp()
                    cache.set(email, verification_code)
                    transaction.on_commit(lambda: verify_account_email.delay(email, verification_code))
                    raise serializers.ValidationError(
                        {"message": "This user is currently not active. Verify your account.", "status": "failed"},
                        code=400
                    )
            else:
                logger.warning(f"Login attempt failed: User {email} not found")
                raise serializers.ValidationError(
                    {"message": "Invalid login details.", "status": "failed"},
                    code=400
                )

            from django.contrib.auth.hashers import check_password

            if not check_password(password, self.user.password):
                logger.warning(f"Login attempt failed: Invalid password for user {email}")
                raise serializers.ValidationError(
                    {"message": "Invalid login details", "status": "failed"},
                    code=400
                )

            logger.info(f"Login successful for user {email}")
            token = self.__get_tokens_for_user()
            return self.user, token

        except ObjectDoesNotExist:
            logger.error(f"User does not exist: {email}")
            raise serializers.ValidationError(
                {"message": "Invalid login details.", "status": "failed"},
                code=400
            )

    def logout(self, token):
        token = RefreshToken(token)
        token.blacklist()

    @transaction.atomic
    def password_reset(self, email):
        try:
            self.user = User.objects.get(email=email)
            if self.user:
                verification_code = generate_otp()
                cache.set(verification_code, email)
                logger.info("Account verified successfully: {}".format(email))
                transaction.on_commit(lambda: send_reset_request_mail.delay(email, verification_code))
        except ObjectDoesNotExist:
            raise serializers.ValidationError(
                {"message": "You are not a user on this application", "status":"failed"},
                code=400
            )

        except Exception as error:
            logger.info("Account verified successfully: {}".format(error))
            raise serializers.ValidationError({'message':str(error), 'status':'failed'})

    @transaction.atomic
    def change_password(self, old_password, new_password):
        token = self.__get_tokens_for_user()
        with transaction.atomic():
            if not self.user.check_password(old_password):
                raise serializers.ValidationError(
                {"message": "Wrong password.", "status":"failed"},
                code=400
            )
            self.user.set_password(new_password)
            self.user.save()
        refresh_token = token.get("refresh")
        self.logout(refresh_token)
        return self.user

    @transaction.atomic
    def password_reset_confirmation(self, verification_code, password):
        email = cache.get(verification_code)
        if email:
            self.user = User.objects.filter(email=email).first()
            if self.user.check_password(password):
                raise serializers.ValidationError(
                {"message": "You can not reset your password to your current password", "status":"failed"},
                code=400
            )
            self.user.set_password(password)
            self.user.save()

            return self.user, self.__get_tokens_for_user()
        raise serializers.ValidationError(
                {"message": "Invalid or expired verification code", "status":"failed"},
                code=400
            )

    def resend_account_verification(self, email):
        try:
            self.user = User.objects.get(email=email)
        except ObjectDoesNotExist:
            raise serializers.ValidationError(
                {"message": "User does not exist", "status":"failed"},
                code=400
            )

        verification_code = generate_otp()
        cache.set(email, verification_code)
        transaction.on_commit(lambda: verify_account_email.delay(email, verification_code))

    @transaction.atomic
    def reset_account_password(self, email, password, verification_code):
        try:
            if cache.get(verification_code) == email:
                self.user = User.objects.get(email=email)

                self.user.is_active = True
                self.user.account_verified = True
                self.user.account_verified_at = timezone.now()
                self.user.set_password(password)
                self.user.save()
                cache.delete(email)
                return self.user, self.__get_tokens_for_user()
            raise serializers.ValidationError(
                {"message": "Invalid link or expired verification code", "status":"failed"},
                code=400
            )
        except ObjectDoesNotExist:
            raise serializers.ValidationError(
                        {"message":"This user does not exist", "status":"failed"},
                        code=400
                    )