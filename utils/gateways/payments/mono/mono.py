import logging
import uuid
from datetime import datetime

from django.conf import settings

import requests
from rest_framework import serializers

from utils.gateways.payments import PaymentClient
from utils.exceptions import ServiceUnavailable

from utils.gateways.payments.mono.dummy import use_dummy_response

logger = logging.getLogger(__name__)


class MonoException(ServiceUnavailable):
    detail = "service unavailable"


class MonoClient(PaymentClient):

    class MonoResponse:
        EXCHANGE_TOKEN = {
            "id": uuid.uuid4()
        }
        INITIATE_PAYMENT = {
              "id": "txreq_AA19LPPlicDUPUl2DrO7QJXU",
              "type": "onetime-debit",
              "amount": 20000,
              "description": "ddddd",
              "reference": "jd3jdjd3937484943",
              "payment_link": "https://connect.withmono.com/?key=live_pk_31d8peH2KYeL0JF6Tvq0&scope=payments&data=%7B%22amount%22%3A20000%2C%22description%22%3A%22ddddd%22%2C%22type%22%3A%22onetime-debit%22%2C%22reference%22%3A%22jd3jdjd3937484943%22%7D", # noqa
              "created_at": "2021-08-04T15:24:11.849Z",
              "updated_at": "2021-08-04T15:24:11.849Z"
        }
        FINALIZE_PAYMENT = {
            "type": "onetime-debit",
            "data": {
                "_id": "62d52dd2ccc45d16611918e4",
                "id": "txd_LobSBDjo89H4diQS",
                "status": "successful",
                "message": "Payment was successful",
                "amount": 20000,
                "description": "description of payment",
                "fee": 4500,
                "currency": "NGN",
                "account": {
                    "_id": "62d52ddc45d16611918d3",
                    "institution": {
                    "name": "KudaBank",
                    "bankCode": "090267",
                    "type": "PERSONAL_BANKING"
                    },
                    "name": "ABDULHAMID TOMIWA HASSAN",
                    "type": "DIGITAL_SAVINGS_ACCOUNT",
                    "accountNumber": "1100001623",
                    "balance": 870982,
                    "currency": "NGN",
                    "bvn": "00000000",
                    "liveMode": True,
                    "timeline": "62d52db8ccc45d1661191129",
                    "created_at": "2022-07-18T09:54:25.289Z",
                    "updated_at": "2022-07-18T11:00:00.260Z"
                },
                "customer": None,
                "reference": "I29FIJ165834838",
                "metadata": {
                    "channel": "wallet"
                },
                "created_at": "2022-07-18T09:54:26.262Z",
                "updated_at": "2022-07-18T09:55:03.625Z"
              }
        }
        SUCCESSFUL_PAYMENT = {"status": True, "data": FINALIZE_PAYMENT}
        IDENTITY = {
            "full_name":"HASSAN ABDULHAMID TOMIWA",
            "email": "ab@mono.co",
            "phone_number" :"08133703766",
            "gender": "male",
            "date_of_birth": datetime.strptime("1990-02-09", '%Y-%m-%d').date(),
            "id_number": "00469141595",
            "metadata": {
                "fullName":"HASSAN ABDULHAMID TOMIWA",
                "email": "ab@mono.co",
                "phone" :"08133703766",
                "gender": "male",
                "dob": "02-09-1990",
                "bvn": "00469141595",
                "maritalStatus": None,
                "addressLine1": "23 shittu animashaun",
                "addressLine2": "Gbagada"
            }
        }

    def __init__(self, *args, **kwargs):
        self.__response_data = None
        self.__base_url = settings.MONO_BASE_URL
        self.__headers = {
            "mono-sec-key": settings.MONO_SEC_KEY,
            "accept": "application/json",
            "content-type": "application/json"
        }
        self.MonoResponse.INITIATE_PAYMENT["reference"] = kwargs.get("reference")
        self.MonoResponse.SUCCESSFUL_PAYMENT["data"]["reference"] = kwargs.get("lookup_id")

    def __build_url(self, endpoint):
        return f"{self.__base_url}/{endpoint}"

    @staticmethod
    def __handle_mono_response(response):
        if response.status_code == 200:
            return response.json() # returns data in this format { "id": "5f171a530295e231abca1153"# }

        elif response.status_code == 400:
            raise serializers.ValidationError({"mono": [response.json()]})
        else:
            logger.info(response.json())
            raise MonoException()

    @use_dummy_response(MonoResponse.EXCHANGE_TOKEN)
    def exchange_token(self, token):
        url = self.__build_url("account/auth")
        data = {
            "token": token
        }
        response = requests.post(url=url, data=data, headers=self.__headers)
        return self.__handle_mono_response(response)

    @use_dummy_response(MonoResponse.INITIATE_PAYMENT)
    def process_charge(self, request_kwargs):
        amount = request_kwargs["amount"]
        reference = request_kwargs["reference"]
        meta = request_kwargs["meta"]
        customer_id = meta["customer_id"]
        description = meta["description"]
        url = self.__build_url("payments/initiate")
        redirect_url = "https://greyswitch.co"
        payload = {
            "amount": str(amount * 100),
            "type": "onetime-debit",
            "description": description,
            "reference": reference,
            "account": customer_id,
            "redirect_url": redirect_url,
            "meta": meta
        }

        response = requests.post(url, json=payload, headers=self.__headers)
        return self.__handle_mono_response(response)

    @use_dummy_response(MonoResponse.SUCCESSFUL_PAYMENT)
    def verify_charge(self, request_kwargs):
        url = self.__build_url("payments/verify")
        reference = request_kwargs["reference"]
        payload = {"reference": reference}
        response = requests.post(url, json=payload, headers=self.__headers)
        self.__response_data = self.__handle_mono_response(response)
        self.__response_data["metadata"] = self.__response_data["meta"]
        if self.__response_data["status"] == "successful":
            return {"status": True, "data": self.__response_data}
        else:
            return {"status": False, "data": self.__response_data}

    @use_dummy_response(MonoResponse.IDENTITY)
    def fetch_identity_data(self, request_kwargs):
        mono_customer_id = request_kwargs["mono_customer_id"]
        url = self.__build_url(f"accounts/{mono_customer_id}/identity")
        response = requests.get(url, headers=self.__headers)
        self.__response_data = self.__handle_mono_response(response)
        data = {
            "full_name": self.__response_data["fullName"],
            "email": self.__response_data["email"],
            "phone_number": self.__response_data["phone"],
            "gender": self.__response_data["gender"],
            "date_of_birth": self.__response_data["dob"],
            "id_number": self.__response_data["bvn"],
            "metadata": self.__response_data
        }
        return data
