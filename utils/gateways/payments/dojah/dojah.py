import datetime
from django.conf import settings
from utils.exceptions import ServiceUnavailable
import requests
import logging
from rest_framework import serializers
logger = logging.getLogger(__name__)

class DojahException(ServiceUnavailable):
    detail = "service unavailable"

class DojahClient:
    
    def __init__(self, *args, **kwargs):
        self.__response_data = None
        self.__base_url = settings.DOJAH_BVN_VERIFICATION_URL
        self.__headers = {
            "content-type": "application/json",
            "appid":settings.DOJAH_APPID,
            "authorization":settings.DOJAH_PRODUCTION_PRIVATE_KEY
        }
        
    @staticmethod
    def __handle_dojah_response(response):
        if response.status_code == 200:
            return response.json() 

        elif response.status_code == 400:
            raise serializers.ValidationError({"dojah": [response.json()]})
        else:
            logger.info(response.json())
            raise DojahException()
        
    def fetch_identity_data(self, bvn):
        
        url = self.__base_url + f'?bvn={bvn}'
        headers = {
            "accept": "application/json",
            'Authorization': self.__headers["authorization"],
            'AppId': self.__headers["appid"]
        }
        response = requests.get(url, headers=headers)

        prefix = "234"

        self.__response_data = self.__handle_dojah_response(response)
        logger.info("Returning bvn credentials for user with bvn: {}".format(bvn))
        data = {
            "full_name": self.__response_data["entity"]["first_name"] + ' ' + self.__response_data["entity"]["last_name"],
            "phone_number": prefix + self.__response_data["entity"]["phone_number1"][1:],
            "gender": self.__response_data["entity"]["gender"],
            "id_number": self.__response_data["entity"]["bvn"],
            "metadata": self.__response_data["entity"]
        }
        return data