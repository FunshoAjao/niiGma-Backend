import logging
import traceback
from rest_framework.views import exception_handler
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from django.http import Http404
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    # Handle specific exceptions
    if isinstance(exc, AuthenticationFailed):
        return Response(
            {"message": "Authentication failed", "status": "failed"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if isinstance(exc, Http404):
        return Response(
            {"message": "Resource not found", "status": "failed"},
            status=status.HTTP_404_NOT_FOUND
        )

    if isinstance(exc, ValidationError):
        error_messages = exc.detail
        first_error = next(iter(error_messages.values())) if isinstance(error_messages, dict) else error_messages

        if isinstance(first_error, list):
            message = first_error[0]
        elif isinstance(first_error, str):
            message = first_error
        else:
            message = "Invalid input."

        return Response(
            {"message": message, "status": "failed"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Handle other known errors
    if response is not None:
        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            return Response(
                {"message": "Authentication failed", "status": "failed"},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        elif response.status_code == status.HTTP_403_FORBIDDEN:
            return Response(
                {"message": f"{response.data['detail']}", "status": "failed"},
                status=status.HTTP_403_FORBIDDEN
            )

        return Response(
            {
                "message": "Internal Server Error",
                "status": "failed",
                "details": str(exc)  # ONLY FOR DEBUGGING!
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # For uncaught exceptions (typically 500s), log details!
    logger.error(
        "Unhandled Exception: %s\nContext: %s\nTraceback: %s",
        str(exc),
        context,
        traceback.format_exc()
    )