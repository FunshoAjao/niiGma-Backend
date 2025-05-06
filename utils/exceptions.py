from rest_framework import exceptions, status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class ServiceUnavailable(APIException):
    status_code = 503
    default_detail = 'You may not use this service at this time, please try again later.'
    default_code = 'service_unavailable'


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)
    if isinstance(exc, (exceptions.AuthenticationFailed, exceptions.NotAuthenticated)):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        response.data = {
            "detail": ["Authentication credentials were not provided."]
        }

    # Now add the HTTP status code to the response
    if response is not None:
        customized_response = {"message": "request could not be processed", 'errors': {}}

        for key, value in response.data.items():
            customized_response['errors'][key] = value

        response.data = customized_response

    return response