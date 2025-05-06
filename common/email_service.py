import boto3
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class AWSEmailService:
    def __init__(self):
        self.client = boto3.client(
            "ses",
            aws_access_key_id=settings.AWS_SES_ACCESS_KEY,
            aws_secret_access_key=settings.AWS_SES_SECRET_KEY,
            region_name=settings.AWS_SES_REGION
        )

    def send_email(self, recipient, subject, body):
        try:
            response = self.client.send_email(
                Source=settings.DEFAULT_FROM_EMAIL,
                Destination={"ToAddresses": [recipient]},
                Message={
                    "Subject": {"Data": subject},
                    "Body": {"Text": {"Data": body}},
                },
            )
            logger.info(f"Email sent successfully: {response}")
            return response
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return None
