from smtplib import SMTPServerDisconnected

from celery import shared_task
from core.celery import app as celery_app
from urllib.parse import unquote, urlencode

from utils.helpers.services import send_template_email
from django.conf import settings
from ..models import User
from rest_framework import serializers
import logging
logger = logging.getLogger(__name__)

@celery_app.task(name="send_sign_up_email")
def send_sign_up_email(email, verification_code):
    logger.info(f"[TASK START] send_sign_up_email -> {email}")
    try:
        user = User.objects.filter(email=email).first()
        if not user:
            logger.warning(f"[TASK] No user found for email: {email}")
            return

        send_template_email(
            "signup.html",
            email,
            "Welcome Onboard",
            username=user.first_name + ' ' + user.last_name,
            otp_code=verification_code,
            verification_link=''
        )

        logger.info(f"[TASK COMPLETE] Email sent to {email}")
    except Exception as e:
        logger.error(f"[TASK ERROR] Failed to send sign_up_email to {email}: {e}", exc_info=True)
        raise

@celery_app.task(name="verify_account_email")
def verify_account_email(email, verification_code):
    user = User.objects.get(email=email)

    send_template_email(
        "verify_account_email.html",
        email,
        "Verify Account",
        **{
            "username": user.first_name + ' ' + user.last_name,
            "otp_code": verification_code
        },
    )
    logger.info("Verify account email sent successfully: {}".format(email))

@celery_app.task(name="send_otp")
def send_otp(email, verification_code):
    logger.info("Sending otp for user: {}".format(email))
    user = User.objects.filter(email=email).first()

    send_template_email(
        "otp_mail.html",
        email,
        "OTP Mail",
        **{
            "username": user.first_name + ' ' + user.last_name,
            "otp_code": verification_code
        },
    )
    logger.info("Otp sent successfully: {}".format(email))

@celery_app.task(name="send_account_verification_email")
def send_account_verification_email(email):
    logger.info("verification email for user: {}".format(email))
    user = User.objects.get(email=email)

    send_template_email(
        "otp_verification.html",
        email,
        "Account Verification Successful",
        **{
            "username": user.first_name + ' ' + user.last_name,
        },
    )
    logger.info("Account verified successfully: {}".format(email))

@celery_app.task(name="send_reset_request_mail")
def send_reset_request_mail(email, verification_code):
    logger.info("----------------About to send a reset email for this user: {}".format(email))
    user = User.objects.filter(email=email).first()

    send_template_email(
        "reset_password.html",
        email,
        "Password Reset",
        **{
            "username": user.first_name + ' ' + user.last_name,
            "otp_code": verification_code
        },
    )