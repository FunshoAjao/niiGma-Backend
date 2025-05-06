import requests
from django.conf import settings
from requests import Timeout, TooManyRedirects
from requests.exceptions import ConnectionError
from rest_framework import serializers

from utils.exceptions import ServiceUnavailable


class TermiiClient:
    termii_api_key = settings.TERMII_API_KEY
    url = "https://v3.api.termii.com/api/sms/send"
    headers = {
                'Content-Type': 'application/json',
            }
    def __init__(self, phone_number, message):
        self.phone_number = phone_number
        self.message = message

    def __send_sms_message(self):
        print(self.phone_number)
        data = {
            "to": self.phone_number,
            "from": "N-Alert",
            "sms": self.message,
            "type": "plain",
            "channel": "dnd",
            "api_key": self.termii_api_key
        }
        
        try:
            response = requests.request("POST", self.url, headers=self.headers, json=data)
            print(response.text)
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
