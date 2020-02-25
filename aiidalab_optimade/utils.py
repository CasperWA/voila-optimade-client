from typing import Tuple, List, Union
from urllib.parse import urlencode
import requests
from simplejson import JSONDecodeError

from aiidalab_optimade.exceptions import (
    ApiVersionError,
    InputError,
    NonExistent,
    NotOkResponse,
)


# Supported OPTiMaDe spec version
__optimade_version__ = "0.10.1"

TIMEOUT_SECONDS = 10  # Seconds before URL query timeout is raised

PROVIDERS_URL = "https://providers.optimade.org/v1/links"


def fetch_providers(providers_url: str = None) -> list:
    """ Fetch OPTiMaDe database providers (from Materials-Consortia)

    :param providers_url: String with URL to providers.json file
    """
    if providers_url and not isinstance(providers_url, str):
        raise TypeError("providers_url must be a string")

    if not providers_url:
        providers_url = PROVIDERS_URL

    try:
        providers = requests.get(providers_url, timeout=TIMEOUT_SECONDS)
    except Exception:
        raise NonExistent("The URL cannot be opened: {}".format(providers_url))

    if providers.status_code == 200:
        providers = providers.json()
    else:
        raise NotOkResponse("Received a {} response".format(providers.status_code))

    # Return list of providers
    return providers["data"]


def fetch_provider_child_dbs(base_url: str) -> list:
    """Fetch an OPTiMaDe provider's child databases"""
    if not isinstance(base_url, str):
        raise TypeError("base_url must be a string")

    links_endpoint = "/links"
    links_endpoint = (
        base_url + links_endpoint[1:]
        if base_url.endswith("/")
        else base_url + links_endpoint
    )

    try:
        implementations = requests.get(links_endpoint, timeout=TIMEOUT_SECONDS)
    except Exception:
        raise NonExistent(f"The URL cannot be opened: {links_endpoint}")

    if implementations.status_code == 200:
        implementations = implementations.json()
    else:
        implementations = {}

    # Return all implementations of type "child"
    implementations = [
        implementation
        for implementation in implementations.get("data", [])
        if implementation.get("type", "") == "child"
    ]

    # If there are no implementations, try if index meta-database == implementation database
    if not implementations:
        structures_endpoint = "/structures?page_limit=1"
        structures_endpoint = (
            base_url + structures_endpoint[1:]
            if base_url.endswith("/")
            else base_url + structures_endpoint
        )

        try:
            implementations = requests.get(structures_endpoint, timeout=TIMEOUT_SECONDS)
        except Exception:  # pylint: disable=broad-except
            return []

        if implementations.status_code == 200:
            implementations = implementations.json()
        else:
            return []

        attributes = implementations.get("meta", {}).get("provider", {})
        implementations = []
        if attributes:
            attributes.update({"base_url": base_url})
            for field in ("prefix", "index_base_url"):
                attributes.pop(field, None)
            implementations = [{"attributes": attributes}]

        if not implementations:
            implementations = "structures found"

    return implementations


def get_list_of_valid_providers() -> List[Tuple[str, dict]]:
    """ Get curated list of database providers

    Return formatted list of tuples to use with a dropdown-widget.
    """
    providers = fetch_providers()
    res = []

    for provider in providers:
        # Skip if "exmpl"
        if provider["id"] == "exmpl":
            continue

        attributes = provider["attributes"]

        # Skip if there is no base URL
        if attributes["base_url"] is None:
            continue

        # Get versioned base URL
        version_parts = [
            f"/v{__optimade_version__.split('.')[0]}",  # major
            f"/v{'.'.join(__optimade_version__.split('.')[:2])}",  # minor
            f"/v{__optimade_version__}",  # patch
        ]
        for version in version_parts:
            base_url = (
                attributes["base_url"] + version[1:]
                if attributes["base_url"].endswith("/")
                else attributes["base_url"] + version
            )
            if requests.get(f"{base_url}/info").status_code == 200:
                attributes["base_url"] = base_url
                break
        else:
            # Not a valid/supported provider: skip
            continue

        res.append((attributes["name"], attributes))

    return res


def get_list_of_provider_implementations(
    provider_attributes: dict,
) -> List[Tuple[str, dict]]:
    """Get list of provider implementations

    Return formatted list of tuples to use with a dropdown-widget.
    """
    child_dbs = fetch_provider_child_dbs(provider_attributes["base_url"])
    res = []

    if isinstance(child_dbs, str) and child_dbs == "structures found":
        # Use info from provider attributes
        database = {"attributes": provider_attributes}
        database["attributes"]["name"] = "Main database"
        child_dbs = [database]

    for child_db in child_dbs:
        attributes = child_db["attributes"]

        # Skip if there is no base_url
        if attributes["base_url"] is None:
            continue

        res.append((attributes["name"], attributes))

    return res


def validate_api_version(version: str, raise_on_mismatch: bool = True) -> bool:
    """Given an OPTiMaDe API version, validate it against current supported API version"""
    if not version:
        raise InputError("No version found in response")

    if version.startswith("v"):
        version = version[1:]

    if version != __optimade_version__:
        if raise_on_mismatch:
            raise ApiVersionError(
                "Only OPTiMaDe {} is supported. Chosen implementation has {}".format(
                    __optimade_version__, version
                )
            )
        return False

    return True


def perform_optimade_query(  # pylint: disable=too-many-arguments,too-many-branches
    base_url: str,
    endpoint: str = None,
    filter_: Union[dict, str] = None,
    format_: str = None,
    email: str = None,
    fields: str = None,
    limit: int = None,
    offset: int = None,
) -> dict:
    """Perform query of database"""
    queries = {}

    if endpoint is None:
        endpoint = "/structures"
    elif not endpoint.startswith("/"):
        endpoint = "/" + endpoint

    url_path = (
        base_url + endpoint[1:] if base_url.endswith("/") else base_url + endpoint
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
    if offset:
        queries["page_offset"] = offset

    # Make query - get data
    url_query = urlencode(queries)
    response = requests.get("{}?{}".format(url_path, url_query))

    try:
        response = response.json()
    except JSONDecodeError:
        response = {"errors": []}

    return response


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
