from rest_framework.response import Response
from rest_framework import serializers, exceptions, status
from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if isinstance(exc, (exceptions.AuthenticationFailed, exceptions.NotAuthenticated)):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        response.data = {
            "detail": ["Authentication credentials were not provided."]
        }
    
    if response is not None and isinstance(response.data, dict):
            custom_response_data = {
                "status": "failed"
            }

            error_messages = []
            # Iterate over each field in the response data
            for field, errors in response.data.items():
                if isinstance(errors, list):
                    for error in errors:
                        error_messages.append(f"{field}: {error}")
                else:
                    error_messages.append(f"{errors}")

            # If there are error messages, use the first one
            if error_messages:
                # custom_response_data["message"] = "; ".join(error_messages)
                custom_response_data["message"] = error_messages[0]
            else:
                custom_response_data["message"] = "An error occurred."

            # Update the response with custom data
            response.data.clear()
            response.data = custom_response_data

    # For other exceptions, return the default handler's response
    return response

class SerializersException(Exception):
    pass

class CustomSuccessResponse(Response):
    def __init__(self, data=None, message=None, status=200, **kwargs):
        resp = {"status": "success", "entity":data, "message":message}
        # resp.update(data)
        super().__init__(data=resp, status=status, **kwargs)


class CustomErrorResponse(Response):
    def __init__(self, data=None, message=None, status=400, **kwargs):
        # If message is a dictionary (serializer.errors), convert it to a single string
        if isinstance(message, dict):
            message = " ".join([f"{key}: {', '.join(map(str, value))}" for key, value in message.items()])

        resp = {"status": "failed", "entity": data, "message": message}
        super().__init__(data=resp, status=status, **kwargs)


class SerializerCustomErrorResponse(Response):
    def __init__(self, data=None, message=None, status=403, **kwargs):
        resp = {"status": "failed", "entity":data, "message":message}
        
        raise serializers.ValidationError(resp, status)