import requests
from django.conf import settings
from django.db import models
from . import PaymentClient
from .. import ClientParser, ClientException

logger = settings.LOGGER


class PayStackStatus(models.TextChoices):
    SUCCESS = "success"
    FAILED = "failed"


class PayStackException(ClientException):
    pass


class PayStackClient(PaymentClient):

    def build_url(self, endpoint):
        url = f'{self.base_url}/{endpoint}'

        return url

    def __init__(self, **kwargs):
        self.base_url = settings.PAYSTACK_BASE_URL
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.auth_token = self.secret_key
        self.header = {'Authorization': 'Bearer ' + self.auth_token}
        self.__response_data = None
        self.client_parser = ClientParser
        self.client_name = "paystack"

    def process_charge(self, **request_kwargs):
        reference = request_kwargs.pop("reference")
        amount = request_kwargs.pop("amount")
        email = request_kwargs.pop("email")
        callback_url = request_kwargs.pop("callback_url")
        meta = request_kwargs.pop("meta")

        data = {
            "amount": str(amount * 100),
            "email": email,
            "reference": str(reference),
            "callback_url": callback_url,
            "channel": ['card', 'bank', 'ussd', 'qr', 'mobile_money', 'bank_transfer'],
            "metadata": meta
        }
        logger.info(f"{meta['name']} initiated a payment for {meta['channel']}")
        endpoint = "transaction/initialize"
        url = f"{self.base_url}/{endpoint}"
        response = requests.post(url, json=data, headers=self.header)

        return self.__process_initiate_charge_response(data, response)

    def __process_initiate_charge_response(self, request=None, response=None, method="POST"):
        request_parser = self.client_parser(
            method=method,
            request_data=request,
            response=response,
            client=self.client_name
        )
        self.__response_data = request_parser()
        logger.info(self.__response_data)
        try:
            status = self.__response_data["status"]
            data = self.__response_data["data"]
            if status and "authorization_url" in data:
                link = data["authorization_url"]
                return {"link": link}
            else:
                raise ClientException

        except KeyError:
            raise ClientException

    def __requery_charge_transaction(self, lookup_id=None):
        url = self.build_url(f'transaction/verify/{lookup_id}')
        response = requests.get(url, headers=self.header)
        request = {
            "reference": lookup_id
        }
        self.__process_requery_charge_response(request=request, response=response, method="GET")
        self.__response_data = response.json()
        return self.__response_data["data"]

    def bank_account_verify(self, **kwargs):
        account_number = kwargs.get("account_number")
        bank_code = kwargs.get("bank_code")
        url = f'{self.base_url}/bank/resolve?account_number={account_number}&bank_code={bank_code}'
        response = requests.get(url, headers=self.header)
        request = {
            "account_number": account_number,
            "bank_code": bank_code
        }
        self.__process_bank_resolve_response(request=request, response=response, method="GET")
        self.__response_data = response.json()
        if self.__response_data["message"] == "Account number resolved":
            data = True
        else:
            data = False
        return data

    def __process_bank_resolve_response(self, request, response, method):
        request_parser = self.client_parser(
            method=method,
            request_data=request,
            response=response,
            client=self.client_name
        )
        self.__response_data = request_parser()
        try:
            status = self.__response_data["status"]
            data = self.__response_data["data"]

            if status:
                return data

        except KeyError:
            raise ClientException()


    def __process_requery_charge_response(self, request, response, method):
        request_parser = self.client_parser(
            method=method,
            request_data=request,
            response=response,
            client=self.client_name
        )
        self.__response_data = request_parser()
        try:
            status = self.__response_data["status"]
            data = self.__response_data["data"]

            if status and data["status"] == "success":
                return data

        except KeyError:
            raise ClientException

    def verify_charge(self, **requery_meta):
        try:
            logger.info(requery_meta)
            payment_reference = str(requery_meta["lookup_id"])
            payment_amount = requery_meta["amount"]
            logger.info(f"commencing charge verification for  reference: {payment_reference}")
            data = self.__requery_charge_transaction(payment_reference)
            client_payment_reference = data.get("reference")
            client_amount = data.get("amount")
            client_status = data.get("status")
            reference_status = client_payment_reference == payment_reference
            amount_status = client_amount >= payment_amount
            status_status = client_status == PayStackStatus.SUCCESS
            logger.info(f"{reference_status} {amount_status} {status_status}")
            logger.info(self.__response_data)
            if reference_status and amount_status and status_status:
                return {"status": True, "data": self.__response_data}
            else:
                return {"status": False, "data": self.__response_data}
        except KeyError as err:
            raise Exception(err)


