"""Class that encapsilates REST functionality for a single API endpoint."""

__author__ = "Tom Goetz"
__copyright__ = "Copyright Tom Goetz"
__license__ = "GPL"

import os
import logging
import json
import enum


class RestExceptionPers(Exception):
    """Exception caught while making REST calls."""

    def __init__(self, e, error, printable_fields=[]):
        """Create a new instance of the RestException class."""
        self.printable_fields = ['inner_exception', 'error'] + printable_fields
        self.inner_exception = e
        self.error = error
        super().__init__()

    def __repr__(self):
        """Return a string representation of a RestException instance."""
        fields = {printable_field : getattr(self, printable_field) for printable_field in self.printable_fields}
        return f'<{self.__class__.__name__}() {repr(fields)}>'

    def __str__(self):
        """Return a string representation of a RestException instance."""
        return self.__repr__()


class RestCallExceptionPers(RestExceptionPers):
    """Exception caught while processing REST responses."""

    def __init__(self, e, url, response, error):
        """Create a new instance of the RestException class."""
        super().__init__(e, error, ['url', 'response'])
        self.url = url
        self.response = response


class RestResponseExceptionPers(RestExceptionPers):
    """Exception caught while processing REST responses."""

    def __init__(self, e, response, error):
        """Create a new instance of the RestException class."""
        super().__init__(e, error, ['response'])
        self.response = response


class RestProtocolPers(enum.Enum):
    """Enums for the protocols used for REST requests."""

    http    = 'http'
    https   = 'https'


class RestClientPers():
    """Class that encapsilates REST functionality for a single API endpoint."""

    logger = logging.getLogger(__file__)

    agents = {
        'Chrome_Linux'  : 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/1337 Safari/537.36',
        'Firefox_MacOS' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:66.0) Gecko/20100101 Firefox/66.0'
    }
    agent = agents['Firefox_MacOS']

    default_headers = {
        # 'User-Agent'    : agent,
        # 'Accept'        : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }

    def __init__(self, session, host, base_route, protocol=RestProtocolPers.https, port=443, headers=None, aditional_headers={}):
        """Return a new RestClient instance given a requests session and the base URL of the API."""
        self.session = session
        self.host = host
        self.protocol = protocol
        self.port = port
        self.base_route = base_route
        if headers:
            self.headers = headers
        else:
            self.headers = self.default_headers.copy()
        self.headers.update(aditional_headers)

    @classmethod
    def inherit(cls, rest_client, route):
        """Create a new RestClient object from a RestClient object. The new object will handle an API endpoint that is a child of the old RestClient."""
        return RestClientPers(rest_client.session, rest_client.host, f'{rest_client.base_route}/{route}',
                              protocol=rest_client.protocol, port=rest_client.port, headers=rest_client.headers)

    def url(self, leaf_route=None):
        """Return the url for the REST endpoint including leaf if supplied."""
        if leaf_route is not None:
            path = '%s/%s' % (self.base_route, leaf_route)
        else:
            path = self.base_route
        if (self.protocol == RestProtocolPers.https and self.port == 443) or (self.protocol == RestProtocolPers.http and self.port == 80):
            return f'{self.protocol.name}://{self.host}/{path}'
        return f'{self.protocol.name}://{self.host}:{self.port}/{path}'

    def get(self, leaf_route, additional_headers=None, params=None, ignore_errors=None):
        """Make a REST API call using the GET method."""
        if ignore_errors is None:
            ignore_errors = []
        if params is None:
            params = {}
        if additional_headers is None:
            additional_headers = {}
        total_headers = self.headers.copy()
        total_headers.update(additional_headers)
        url = self.url(leaf_route)
        try:
            response = self.session.get(url, headers=total_headers, params=params)
        except Exception as e:
            raise RestCallExceptionPers(e, leaf_route, None, f'GET {url} failed: {e}')
        try:
            response.raise_for_status()
            return response
        except Exception as e:
            if response.status_code not in ignore_errors:
                raise RestCallExceptionPers(e, leaf_route, response, f'GET {response.url} failed ({response.status_code}): {response.text}')

    def post(self, leaf_route, aditional_headers, params, data):
        """Make a REST API call using the POST method."""
        total_headers = self.headers.copy()
        total_headers.update(aditional_headers)
        url = self.url(leaf_route)
        try:
            response = self.session.post(self.url(leaf_route), headers=total_headers, params=params, data=data)
        except Exception as e:
            raise RestCallExceptionPers(e, leaf_route, None, f'POST {url} failed: {e}')
        try:
            response.raise_for_status()
            return response
        except Exception as e:
            raise RestCallExceptionPers(e, leaf_route, response, f'POST {response.url} failed ({response.status_code}): {response.text}')

    @classmethod
    def __convert_to_json(cls, object):
        return object.__str__()

    @classmethod
    def save_json_to_file(cls, filename, json_data):
        """Save JSON formatted data to a file."""
        with open(filename, 'w') as file:
            file.write(json.dumps(json_data, default=cls.__convert_to_json))

    def __download_file(self, leaf_route, params=None, ignore_errors=None):
        """Download data from a REST API and save it to a file."""
        if ignore_errors is None:
            ignore_errors = []
        return self.get(leaf_route, params=params, ignore_errors=ignore_errors).json()

    def ___save_json_to_file(self, filename, response):
        try:
            self.save_json_to_file(filename, response.json())
        except Exception as e:
            raise RestResponseExceptionPers(e, response, error=f'failed to save as json: {e} ({response.content})')

    def download_json_file(self, leaf_route, params=None, ignore_errors=None):
        """Download JSON formatted data from a REST API."""
        if ignore_errors is None:
            ignore_errors = []
        return self.__download_file(leaf_route, params, ignore_errors)

    @classmethod
    def save_binary_file(cls, filename, response):
        """Save binary data to a file."""
        try:
            with open(filename, 'wb') as file:
                for chunk in response:
                    file.write(chunk)
        except Exception as e:
            raise RestResponseExceptionPers(e, response, error=f'failed to save as binary: {e} ({response.content})')

    def download_binary_file(self, leaf_route, filename, overwite=True, params=None):
        """Download binary data from a REST API and save it to a file."""
        self.__download_file(self.save_binary_file, leaf_route, filename, overwite, params)
