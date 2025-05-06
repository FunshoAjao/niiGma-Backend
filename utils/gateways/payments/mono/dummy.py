import copy
from functools import wraps

from django.conf import settings


def make_dummy_response(dummy_response, *args, **kwargs):
    return copy.deepcopy(dummy_response)


def use_dummy_response(dummy_response):
    """
    indicates if a function should return a mock response
    """

    def method_decor(wrapped_method):
        @wraps(wrapped_method)
        def wrapper(*args, **kwargs):
            response = {
                True: lambda *a, **kw: make_dummy_response(dummy_response, *a, **kw),
                False: wrapped_method
            }[settings.USE_CLIENT_DUMMY_RESPONSES](*args, **kwargs)

            return response

        return wrapper

    return method_decor
