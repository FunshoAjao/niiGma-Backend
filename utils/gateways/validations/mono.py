import requests
from django.conf import settings
from requests import Timeout, TooManyRedirects
from requests.exceptions import ConnectionError
from rest_framework import serializers

from utils.exceptions import ServiceUnavailable


class MonoClient:
    mono_key = settings.MON0_KEY
    url = "https://api.withmono.com/v3/lookup/nin"
    bank_account_url = "https://api.withmono.com/v3/lookup/account-number"
    headers = {
                'Content-Type': 'application/json',
                'mono-sec-key': mono_key
            }
    __bank_headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    def __init__(self, nin=None, rc_number=None, nip_code = None, account_number = None):
        self.nin = nin
        self.nip_code = nip_code
        self.account_number = account_number
        self.bank_url = settings.FETCH_BANK_DETAILS
        self.rc_number_url = f"https://api.withmono.com/v3/lookup/cac?search={rc_number}"

    def __validate_nin_number(self):
        data = {
            "nin":self.nin
        }
        
        try:
            response = requests.request("POST", self.url, headers=self.headers, json=data)
            
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise ServiceUnavailable(detail={"message": e})
       
        return response
    
    def __validate_rc_number(self):
        try:
            response = requests.request("GET", self.rc_number_url, headers=self.headers)
            
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise ServiceUnavailable(detail={"message": e})
       
        return response
    
    def __bank_details(self):
        try:
            response = requests.request("GET", self.bank_url, headers=self.__bank_headers)
            
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise ServiceUnavailable(detail={"message": e})
       
        return response
    
    def __account_details(self):
        data = {
            "nip_code":self.nip_code,
            "account_number":self.account_number
        }
        
        try:
            response = requests.request("POST", self.bank_account_url, headers=self.headers, json=data)
            
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise ServiceUnavailable(detail={"message": e})
       
        return response

    def process_request(self):
        nin_response = self.__validate_nin_number()
        if nin_response.status_code == 200 or nin_response.json()['status'] == 'successful':
            return nin_response.status_code, nin_response.json()['data']
        elif nin_response.status_code == 400:
            raise serializers.ValidationError(detail={
                "NIN": [nin_response.json()["message"]]
            })

        raise ServiceUnavailable(nin_response.json())
    
    def process_rc_number_request(self):
        rc_number_response = self.__validate_rc_number()
        if rc_number_response.status_code == 200 or rc_number_response.json()['status'] == 'successful':
            return rc_number_response.status_code, rc_number_response.json()['data']
        elif rc_number_response.status_code == 400 or rc_number_response.status_code == 404: 
            raise serializers.ValidationError(detail={
                "Rc_Number": [rc_number_response.json()["message"]]
            })

        raise ServiceUnavailable(rc_number_response.json()["message"])
    
    def fetch_bank_details(self):
        bank_details = self.__bank_details()
        if bank_details.status_code == 200 or bank_details.json()['status'] == 'successful':
            return bank_details.status_code, bank_details.json()['data']
        elif bank_details.status_code == 400 or bank_details.status_code == 404: 
            raise serializers.ValidationError(detail={
                "Error occurred": [bank_details.json()["message"]]
            })

        raise ServiceUnavailable(bank_details.json()["message"])
    
    def fetch_account_details(self):
        account_details = self.__account_details()
        if account_details.status_code == 200 or account_details.json()['status'] == 'successful':
            return account_details.status_code, account_details.json()['data']
        elif account_details.status_code == 400 or account_details.status_code == 404: 
            raise serializers.ValidationError(detail={
                "Error occurred": [account_details.json()["message"]]
            })

        raise ServiceUnavailable(account_details.json()["message"])