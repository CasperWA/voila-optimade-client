from typing import Union
from urllib.parse import urlencode

import requests


class OptimadeImporter:
    """OPTiMaDe v0.10.0"""

    def __init__(self, base_url: str):
        self.base_url = base_url

    def query(  # pylint: disable=too-many-arguments
        self,
        endpoint: str = None,
        filter_: Union[dict, str] = None,
        format_: str = None,
        email: str = None,
        fields: str = None,
        limit: int = None,
    ) -> dict:
        """Perform query of database"""
        queries = {}

        if endpoint is None:
            endpoint = "/structures"
        elif not endpoint.startswith("/"):
            endpoint = "/" + endpoint

        url_path = (
            self.base_url + endpoint[1:]
            if self.base_url.endswith("/")
            else self.base_url + endpoint
        )

        if filter_ is not None:
            if isinstance(filter_, dict):
                pass
            elif isinstance(filter_, str):
                queries["filter"] = filter_
            else:
                raise TypeError("'filter_' must be either a dict or a str")

        if format_:
            queries["response_format"] = format_
        if email:
            queries["email_address"] = email
        if fields:
            queries["response_fields"] = fields
        if limit:
            queries["page_limit"] = limit

        # Make query - get data
        url_query = urlencode(queries)
        response = requests.get("{}?{}".format(url_path, url_query))

        if response.status_code >= 400:
            raise ImportError(
                "Query returned HTTP status code: {}".format(response.status_code)
            )
        if response.status_code != 200:
            print("Query returned HTTP status code: {}".format(response.status_code))

        return response.json()
