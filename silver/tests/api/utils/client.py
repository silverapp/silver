import json
import numbers
from collections import OrderedDict
from decimal import Decimal

from rest_framework.exceptions import ErrorDetail
from rest_framework.test import APIClient


class JSONApiClient(APIClient):
    def generic(self, *args, **kwargs):
        if 'format' not in kwargs:
            kwargs['format'] = 'json'

        response = super(JSONApiClient, self).generic(*args, **kwargs)
        # some response can return empty responses
        if hasattr(response, 'data'):
            response.data = self._to_dict(response.data)

        return response

    def _to_dict(self, response):
        if isinstance(response, (str, bytes)):
            try:
                candidate_response = json.loads(response)
                if isinstance(candidate_response, numbers.Number):
                    return response

                return candidate_response

            except ValueError:
                pass

        if isinstance(response, OrderedDict):
            response = dict(response)

        if isinstance(response, (list, set)):
            response = [self._to_dict(item) for item in response]
        elif isinstance(response, dict):
            response = {key: self._to_dict(response[key]) for key in response}
        elif isinstance(response, Decimal):
            response = str(response)
        elif isinstance(response, ErrorDetail):
            response = str(response)

        return response
