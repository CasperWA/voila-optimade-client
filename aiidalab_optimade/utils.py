from typing import Tuple, List
import requests

from optimade import __api_version__

from aiidalab_optimade.exceptions import (
    ApiVersionError,
    InputError,
    NonExistent,
    NotOkResponse,
)

TIMEOUT_SECONDS = 10  # Seconds before URL query timeout is raised

PROVIDERS_URL = "https://www.optimade.org/providers/links"


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
        raise NonExistent("The URL cannot be opened: {}".format(links_endpoint))

    if implementations.status_code == 200:
        implementations = implementations.json()
    else:
        implementations = {}

    # Return all implementations of type "child"
    return [
        implementation
        for implementation in implementations.get("data", [])
        if implementation.get("type", "") == "child"
    ]


def get_list_of_valid_providers() -> List[Tuple[str, dict]]:
    """ Get curated list of database providers

    Return formatted list of tuples to use for a dropdown-widget.
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

        provider_name = attributes.pop("name")
        res.append((provider_name, attributes))

    return res


def get_list_of_provider_implementations(
    provider_attributes: str = None,
) -> List[Tuple[str, dict]]:
    """Get list of provider implementations"""
    child_dbs = fetch_provider_child_dbs(provider_attributes["base_url"])
    res = []

    for child_db in child_dbs:
        attributes = child_db["attributes"]

        # Skip if there is no base_url
        if attributes["base_url"] is None:
            continue

        child_db_name = attributes.pop("name")
        res.append((child_db_name, attributes))

    return res


def validate_api_version(version: str, raise_on_mismatch: bool = True) -> bool:
    """Given an OPTiMaDe API version, validate it against current supported API version"""
    if not version:
        raise InputError("No version found in response")

    if version.startswith("v"):
        version = version[1:]

    if version != __api_version__:
        if raise_on_mismatch:
            raise ApiVersionError(
                "Only OPTiMaDe {} is supported. Chosen implementation has {}".format(
                    __api_version__, version
                )
            )
        return False

    return True
