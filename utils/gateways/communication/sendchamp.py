import logging
import requests
from django.conf import settings
from requests import Timeout, TooManyRedirects
from requests.exceptions import ConnectionError
from rest_framework import serializers
logger = logging.getLogger(__name__)
from utils.exceptions import ServiceUnavailable


class SendChampClient:
    
    def __init__(self, phone_number, message, *args, **kwargs):
        self.phone_number = phone_number
        self.message = message
        self.__url = settings.SENDCHAMP_URL
        self.__headers = {
                    "Accept": "application/json,text/plain,*/*",
                    "Content-Type": "application/json",
                    "Authorization": 'Bearer '+ settings.SENDCHAMP_AUTHORIZATION_KEY
                }
        self.__sender_name = settings.SENDCHAMP_SENDER_NAME
        

    def __send_sms_message(self):
        payload = {
            "to": [self.phone_number],
            "message": self.message,
            "sender_name": self.__sender_name,
            "route": "non_dnd"
        }
        
        try:
            response = requests.request("POST", self.__url, json=payload, headers=self.__headers)
            logger.info("OTP sent successfully: {}".format(self.phone_number))
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise ServiceUnavailable(detail={"message": e})

        return response

    def process_request(self):
        sms_response = self.__send_sms_message()
        if sms_response.status_code == 200:
            return
        if sms_response.status_code == 400:
            raise serializers.ValidationError(detail={
                "phone_number": [sms_response.json()["message"]]
            })

        raise ServiceUnavailable(sms_response.json())
