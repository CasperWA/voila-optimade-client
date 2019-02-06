# -*- coding: utf-8 -*-

# Python 2/3 compatibility
from __future__ import print_function

# Imports
import requests
from .exceptions import ApiVersionError


class OptimadeImporter(object):
    """
    OPTiMaDe v0.9.5 and v0.9.7a
    """

    def __init__(self, **kwargs):
        self.db = kwargs["name"] if "name" in kwargs else "cod"

        self.db_baseurl = kwargs["url"] if "url" in kwargs else \
            "http://www.crystallography.net/cod/optimade"

        self.api_version = self._set_api_version()

    def _set_api_version(self):
        endpoint = "/info"
        url = ''.join([self.db_baseurl, endpoint])
        r = requests.get(url)

        if r.status_code != 200:
            raise ImportError("Query returned HTTP status code: {}".format(
                r.status_code))

        response = r.json()
        _api_version = response["meta"]["api_version"][1:]

        try:
            _api_version = tuple(int(i) for i in _api_version.split('.'))
        except ValueError:
            # Remove 'alpha' from PATCH number
            _api_version = _api_version.split('.')
            _api_version[-1] = _api_version[-1][0]

        try:
            _api_version = tuple(int(i) for i in _api_version)
        except Exception:
            raise ApiVersionError("API version should be a tuple of integers")

        return _api_version

    def query(self, filter_=None, **kwargs):
        """ Perform query of database
        :param filter_: dict: k,v-pairs of filters
        :param limit: int: "response_limit" query parameter
        """
        # Get OPTiMaDe queries if they are provided
        format_ = kwargs["format_"] if "format_" in kwargs else None
        email = kwargs["email"] if "email" in kwargs else None
        fields = kwargs["fields"] if "fields" in kwargs else None
        limit = kwargs["limit"] if "limit" in kwargs else None

        # Type checks
        if not isinstance(filter_, dict):
            raise TypeError("filter_ must be a dict")
        if format_ is not None and not isinstance(format_, str):
            raise TypeError("format_ must be a string")
        if limit is not None and not isinstance(limit, int):
            raise TypeError("limit must be an integer")

        # Initiate
        query_str = ""
        idn = None

        # Get filters
        if filter_ is not None:
            endpoint = "/structures"
            if "id" in filter_:
                try:
                    idn = int(filter_["id"])
                except ValueError:
                    # Return all structures - id not typed in correctly
                    idn = None
        else:
            endpoint = "/all"

        # Write query
        if idn:
            query_str = "/{}".format(idn)
        else:
            queries = list()
            if format_:
                queries.append("response_format={}".format(format_))
            if email:
                queries.append("email_address={}".format(email))
            if fields:
                queries.append("response_fields={}".format(fields))
            if limit:
                queries.append("response_limit={}".format(limit))

            query_str = "?{}".format("&".join(queries))

        # Make query - get data
        url = ''.join([self.db_baseurl, endpoint, query_str])
        r = requests.get(url)

        if r.status_code >= 400:
            raise ImportError("Query returned HTTP status code: {}".format(
                r.status_code))
        elif r.status_code != 200:
            print("Query returned HTTP status code: {}".format(r.status_code))

        response = r.json()

        return response
