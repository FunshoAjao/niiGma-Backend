import abc

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from firebase_admin import messaging
import logging
logger = logging.getLogger(__name__)

class DeviceInterface(abc.ABC):
    @abc.abstractmethod
    def send_push_notification(
        self, title: str, body: str, registration_token: str
    ) -> None:
        pass


class WebPushNotification(DeviceInterface):
    def send_push_notification(
        self, title: str, body: str, registration_token: str, route: str = None
    ) -> None:
        """Send web push notifications to users"""
        message = messaging.Message(
            webpush=messaging.WebpushConfig(
                notification=messaging.WebpushNotification(
                    title="FundusAI",
                    body=f"{title}",
                    icon="https://res.cloudinary.com/dv86ryr55/image/upload/v1749732930/Niigma_logo_sbuu9t.jpg",  # URL to the icon
                ),
                data={"summary": f"{body}"},
            ),
            data={"route": route} if route else {},
            token=registration_token,
        )
        response = messaging.send(message)
        logger.info(f"Successfully sent message: {response}")


class AndroidPushNotification(DeviceInterface):
    def send_push_notification(
        self, title: str, body: str, registration_token: str, route: str = None
    ) -> None:
        """Send push notifications to Android devices"""
        message = messaging.Message(
            android=messaging.AndroidConfig(
                notification=messaging.AndroidNotification(
                    title=title,
                    body=body,
                    icon="https://res.cloudinary.com/dv86ryr55/image/upload/v1749732930/Niigma_logo_sbuu9t.jpg",
                    color="#00BCD4",  # More enticing, modern teal
                ),
            ),
            data={"route": route} if route else {},
            token=registration_token,
        )
        response = messaging.send(message)
        print(f"Successfully sent Android push message: {response}")
        logger.info("Successfully sent Android push message: %s", response)


class IOSPushNotification(DeviceInterface):
    def send_push_notification(
        self, title: str, body: str, registration_token: str, route: str = None
    ) -> None:
        """Send push notifications to iOS devices"""
        message = messaging.Message(
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(title=title, body=body),
                        badge=1,
                        sound="default",
                    ),
                ),
                fcm_options=messaging.APNSFCMOptions(
                    image="https://res.cloudinary.com/dv86ryr55/image/upload/v1749732930/Niigma_logo_sbuu9t.jpg"  # URL to the icon
                ),
            ),
            data={"route": route} if route else {},
            token=registration_token,
        )
        response = messaging.send(message)
        logger.info("Successfully sent iOS push message: %s", response)


class PushNotificationService:
    """Class for handling various device type notifications"""

    def __init__(self, device_type, device=None):
        self.device_type = device_type
        self.device = device
        
        if self.device_type == "web":
            self.device = WebPushNotification()
        elif self.device_type == "android":
            self.device = AndroidPushNotification()
        elif self.device_type == "ios":
            self.device = IOSPushNotification()
        else:
            raise ValueError("Unsupported device type")

    def send_push_notification(
        self, title: str, body: str, registration_token: str, route: str = None
    ) -> None:
        self.device.send_push_notification(title, body, registration_token, route)