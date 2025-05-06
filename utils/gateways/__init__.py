import logging

from utils.exceptions import ServiceUnavailable

logger = logging.getLogger(__name__)


class ClientParser:
    def __init__(self, method, request_data, response, client) -> None:
        self.response = response
        self.status_code = self.response.status_code
        self.request_data = request_data
        self.method=method
        self.client = client

    def __call__(self, *args, **kwargs):
        response = self.__parse_response()
        return response


class ClientException(ServiceUnavailable):
    message = "client unavailable"
