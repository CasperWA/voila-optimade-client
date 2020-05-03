import logging
import re
from typing import Tuple, List, Union
from urllib.parse import urlencode

try:
    import simplejson as json
except (ImportError, ModuleNotFoundError):
    import json

from json import JSONDecodeError

import requests

from optimade.models import ProviderResource

from aiidalab_optimade.exceptions import (
    ApiVersionError,
    InputError,
)


LOGGER = logging.getLogger("OPTIMADE_Client")
LOGGER.setLevel(logging.DEBUG)

DEBUG_HANDLER = logging.FileHandler("optimade_client_full.log")
DEBUG_HANDLER.setLevel(logging.DEBUG)

INFO_HANDLER = logging.FileHandler("optimade_client.log")
INFO_HANDLER.setLevel(logging.INFO)

DEBUG_FORMATTER = logging.Formatter(
    "[%(name)s %(levelname)s %(filename)s:%(lineno)d] %(message)s"
)
INFO_FORMATTER = logging.Formatter("[%(levelname)s] %(message)s")
DEBUG_HANDLER.setFormatter(DEBUG_FORMATTER)
INFO_HANDLER.setFormatter(INFO_FORMATTER)

LOGGER.addHandler(DEBUG_HANDLER)
LOGGER.addHandler(INFO_HANDLER)

# Supported OPTIMADE spec version
__optimade_version__ = "0.10.1"

TIMEOUT_SECONDS = 10  # Seconds before URL query timeout is raised

PROVIDERS_URL = "https://providers.optimade.org/v1"


def perform_optimade_query(  # pylint: disable=too-many-arguments,too-many-branches
    base_url: str,
    endpoint: str = None,
    filter: Union[dict, str] = None,  # pylint: disable=redefined-builtin
    response_format: str = None,
    response_fields: str = None,
    email_address: str = None,
    page_limit: int = None,
    page_offset: int = None,
) -> dict:
    """Perform query of database"""
    queries = {}

    if endpoint is None:
        endpoint = "/structures"
    elif not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"

    url_path = (
        base_url + endpoint[1:] if base_url.endswith("/") else base_url + endpoint
    )

    if filter is not None:
        if isinstance(filter, dict):
            pass
        elif isinstance(filter, str):
            queries["filter"] = filter
        else:
            raise TypeError("'filter' must be either a dict or a str")

    if response_format is None:
        response_format = "json"
    queries["response_format"] = response_format

    if response_fields is not None:
        queries["response_fields"] = response_fields

    if email_address is not None:
        queries["email_address"] = email_address

    if page_limit is not None:
        queries["page_limit"] = page_limit

    if page_offset is not None:
        queries["page_offset"] = page_offset

    # Make query - get data
    url_query = urlencode(queries)
    complete_url = f"{url_path}?{url_query}"
    try:
        response = requests.get(complete_url, timeout=TIMEOUT_SECONDS)
    except Exception as exc:  # pylint: disable=broad-except
        return {
            "errors": f"CLIENT: The URL cannot be opened: {complete_url}. Exception: {exc}"
        }

    try:
        response = response.json()
    except JSONDecodeError:
        return {"errors": "CLIENT: Cannot decode response to JSON format."}

    return response


def fetch_providers(providers_url: str = None) -> list:
    """ Fetch OPTIMADE database providers (from Materials-Consortia)

    :param providers_url: String with versioned base URL to Materials-Consortia providers database
    """
    if providers_url and not isinstance(providers_url, str):
        raise TypeError("providers_url must be a string")

    if not providers_url:
        providers_url = PROVIDERS_URL

    providers = perform_optimade_query(base_url=providers_url, endpoint="/links")
    if handle_errors(providers):
        return []

    return providers.get("data", [])


_VERSION_PARTS = [
    f"/v{__optimade_version__.split('.')[0]}",  # major
    f"/v{'.'.join(__optimade_version__.split('.')[:2])}",  # minor
    f"/v{__optimade_version__}",  # patch
]


def get_versioned_base_url(base_url: str) -> str:
    """Retrieve the versioned base URL
    First, check if the given base URL is already a versioned base URL.
    Then try to going through valid version extensions to the URL.
    """
    for version in _VERSION_PARTS:
        if version in base_url:
            if re.match(fr".+{version}$", base_url):
                return base_url
            if re.match(fr".+{version}/$", base_url):
                return base_url[:-1]
            LOGGER.debug(
                "Found version '%s' in base URL '%s', but not at the end of it.",
                version,
                base_url,
            )
            return ""

    for version in _VERSION_PARTS:
        versioned_base_url = (
            base_url + version[1:] if base_url.endswith("/") else base_url + version
        )
        if requests.get(f"{versioned_base_url}/info").status_code == 200:
            return versioned_base_url

    return ""


def get_list_of_valid_providers() -> List[Tuple[str, dict]]:
    """ Get curated list of database providers

    Return formatted list of tuples to use with a dropdown-widget.
    """
    providers = fetch_providers()
    res = []

    for entry in providers:
        provider = ProviderResource(**entry)

        # Skip if "exmpl"
        if provider.id == "exmpl":
            LOGGER.debug("Skipping example provider.")
            continue

        attributes = provider.attributes

        # Skip if there is no base URL
        if attributes.base_url is None:
            LOGGER.debug("Base URL found to be None for provider: %s", str(provider))
            continue

        versioned_base_url = get_versioned_base_url(attributes.base_url)
        if versioned_base_url:
            attributes.base_url = versioned_base_url
        else:
            # Not a valid/supported provider: skip
            LOGGER.debug(
                "Could not determine versioned base URL for provider: %s", str(provider)
            )
            continue

        res.append((attributes.name, attributes))

    return res


def validate_api_version(version: str, raise_on_fail: bool = True) -> str:
    """Given an OPTIMADE API version, validate it against current supported API version"""
    if not version:
        msg = f"No version found in response. Should have been v{__optimade_version__}"
        if raise_on_fail:
            raise ApiVersionError(msg)
        return msg

    if version.startswith("v"):
        version = version[1:]

    if version != __optimade_version__:
        msg = (
            f"Only OPTIMADE v{__optimade_version__} is supported. "
            f"Chosen implementation has v{version}"
        )
        if raise_on_fail:
            raise ApiVersionError(msg)
        return msg

    return ""


def get_structures_schema(base_url: str) -> dict:
    """Retrieve provider's /structures endpoint schema"""
    result = {}

    endpoint = "/info/structures"
    url_path = (
        base_url + endpoint[1:] if base_url.endswith("/") else base_url + endpoint
    )

    response = requests.get(url_path)

    if response.status_code != 200:
        return result

    properties = response.get("data", {}).get("properties", {})
    output_fields_by_json = response.get("output_fields_by_format", {}).get("json", [])
    for field in output_fields_by_json:
        if field in properties:
            result[field] = properties[field]

    return result


def handle_errors(response: dict) -> str:
    """Handle any errors"""
    if "data" not in response and "errors" not in response:
        raise InputError(f"No data and no errors reported in response: {response}")

    if "errors" in response:
        if "data" in response:
            msg = (
                '<font color="red">Error(s) during querying,</font> but '
                f"<strong>{len(response['data'])}</strong> structures found."
            )
        else:
            msg = (
                '<font color="red">Error during querying, '
                "please try again later.</font>"
            )
        LOGGER.debug("Errored response:\n%s", json.dumps(response, indent=2))
        return msg

    return ""
