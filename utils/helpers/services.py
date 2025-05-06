from datetime import datetime
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail
import random
import logging
import ssl
from smtplib import SMTPException
logger = logging.getLogger(__name__)
from rest_framework import serializers

def send_template_email(template, email, subject, **context):
    logger.info("----------------Sending email for this user: {}".format(email))
    html_message = render_to_string(template, context)
    plain_message = strip_tags(html_message)
    logger.info("Email Template initiated: {}".format(email))

    try:
        send_mail(
            subject,
            plain_message,
            "Lab7ai <{}>".format(settings.EMAIL_HOST_USER),
            [email],
            html_message=html_message,
            fail_silently=False,
            connection=None,
            auth_user=settings.EMAIL_HOST_USER,
            auth_password=settings.EMAIL_HOST_PASSWORD
        )
        logger.info(f"Email sent successfully to user {email}")
    except SMTPException as e:
        logger.error(f"SMTP error while sending email to {email}: {str(e)}")
        raise serializers.ValidationError(
            {"message": f"Failed to send email: {str(e)}", "status": "failed"},
            code=500
        )
    except Exception as e:
        logger.error(f"Unexpected error while sending email to {email}: {str(e)}")
        raise serializers.ValidationError(
            {"message": f"Failed to send email: {str(e)}", "status": "failed"},
            code=500
        )

def generate_otp():
    otp = ''.join(random.choice('0123456789') for _ in range(6))
    return otp

def get_expiration_time():
    return int(5)


def validate_date(date_str):
    try:
        # Ensure the date is in the correct format, e.g., 'YYYY-MM-DD'
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
       raise serializers.ValidationError(
                {"message": f"Invalid date format for {date_str}. Expected format: YYYY-MM-DD", "status":"failed"},
                code=400
            )