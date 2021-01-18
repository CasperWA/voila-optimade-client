from collections import OrderedDict
from enum import Enum, EnumMeta
from pathlib import Path
import re
from typing import Tuple, List, Union, Iterable
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

try:
    import simplejson as json
except (ImportError, ModuleNotFoundError):
    import json

from json import JSONDecodeError

import appdirs
from cachecontrol import CacheControlAdapter
from cachecontrol.caches.file_cache import FileCache
from cachecontrol.heuristics import ExpiresAfter
from pydantic import ValidationError, AnyUrl  # pylint: disable=no-name-in-module
import requests

from optimade.models import LinksResource, OptimadeError, Link, LinksResourceAttributes
from optimade.models.links import LinkType

from optimade_client.exceptions import (
    ApiVersionError,
    InputError,
)
from optimade_client.logger import LOGGER


# Supported OPTIMADE spec versions
__optimade_version__ = ["1.0.0", "1.0.0-rc.2", "1.0.0-rc.1", "0.10.1", "0.10.0"]

TIMEOUT_SECONDS = 10  # Seconds before URL query timeout is raised

PROVIDERS_URLS = [
    "https://providers.optimade.org/v1/links",
    "https://raw.githubusercontent.com/Materials-Consortia/providers/master/src"
    "/links/v1/providers.json",
]

CACHE_DIR = Path(appdirs.user_cache_dir("optimade-client", "CasperWA"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHED_PROVIDERS = CACHE_DIR / "cached_providers.json"

SESSION = requests.Session()
SESSION_ADAPTER = CacheControlAdapter(
    cache=FileCache(CACHE_DIR / ".requests_cache"), heuristic=ExpiresAfter(days=1)
)
SESSION_ADAPTER_DEBUG = CacheControlAdapter()
SESSION.mount("http://", SESSION_ADAPTER)
SESSION.mount("https://", SESSION_ADAPTER)
SESSION.mount("http://localhost", SESSION_ADAPTER_DEBUG)
SESSION.mount("http://127.0.0.1", SESSION_ADAPTER_DEBUG)


class DefaultingEnum(EnumMeta):
    """Override __getitem__()"""

    def __getitem__(cls, name):
        """Log warning and default to "DEFAULT" if name is not valid"""
        if name not in cls._member_map_:
            LOGGER.warning(
                "%r is not a valid button style. Setting button style to 'DEFAULT'. "
                "Valid button styles: %s",
                name,
                list(cls._member_map_.keys()),
            )
            name = "DEFAULT"
        return cls._member_map_[name]


class ButtonStyle(Enum, metaclass=DefaultingEnum):
    """Enumeration of button styles"""

    DEFAULT = "default"
    PRIMARY = "primary"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    DANGER = "danger"


def perform_optimade_query(  # pylint: disable=too-many-arguments,too-many-branches,too-many-locals
    base_url: str,
    endpoint: str = None,
    filter: Union[dict, str] = None,  # pylint: disable=redefined-builtin
    sort: Union[str, List[str]] = None,
    response_format: str = None,
    response_fields: str = None,
    email_address: str = None,
    page_limit: int = None,
    page_offset: int = None,
    page_number: int = None,
) -> dict:
    """Perform query of database"""
    queries = OrderedDict()

    if endpoint is None:
        endpoint = "/structures"
    elif endpoint:
        # Make sure we supply the correct slashed format no matter the input
        endpoint = f"/{endpoint.strip('/')}"

    url_path = (
        base_url + endpoint[1:] if base_url.endswith("/") else base_url + endpoint
    )

    if filter:
        if isinstance(filter, dict):
            pass
        elif isinstance(filter, str):
            queries["filter"] = filter
        else:
            raise TypeError("'filter' must be either a dict or a str")

    if sort is not None:
        if isinstance(sort, str):
            queries["sort"] = sort
        else:
            queries["sort"] = ",".join(sort)

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

    if page_number is not None:
        queries["page_number"] = page_number

    # Make query - get data
    url_query = urlencode(queries)
    complete_url = f"{url_path}?{url_query}"
    LOGGER.debug("Performing OPTIMADE query:\n%s", complete_url)
    try:
        response = SESSION.get(complete_url, timeout=TIMEOUT_SECONDS)
        if response.from_cache:
            LOGGER.debug("Request to %s was taken from cache !", complete_url)
    except (
        requests.exceptions.ConnectTimeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.ReadTimeout,
    ) as exc:
        return {
            "errors": [
                {
                    "detail": (
                        f"CLIENT: Connection error or timeout.\nURL: {complete_url}\n"
                        f"Exception: {exc!r}"
                    )
                }
            ]
        }

    try:
        response = response.json()
    except JSONDecodeError as exc:
        return {
            "errors": [
                {
                    "detail": (
                        f"CLIENT: Cannot decode response to JSON format.\nURL: {complete_url}\n"
                        f"Exception: {exc!r}"
                    )
                }
            ]
        }

    return response


def update_local_providers_json(response: dict) -> None:
    """Update local `providers.json` if necessary"""
    # Remove dynamic fields
    _response = response.copy()
    for dynamic_field in (
        "time_stamp",
        "query",
        "last_id",
        "response_message",
        "warnings",
    ):
        _response.get("meta", {}).pop(dynamic_field, None)

    if CACHED_PROVIDERS.exists():
        try:
            with open(CACHED_PROVIDERS, "r") as handle:
                _file_response = json.load(handle)
        except JSONDecodeError:
            pass
        else:
            if _file_response == _response:
                LOGGER.debug("Local %r is up-to-date", CACHED_PROVIDERS.name)
                return

    LOGGER.debug(
        "Creating/updating local file of cached providers (%r).", CACHED_PROVIDERS.name
    )
    with open(CACHED_PROVIDERS, "w") as handle:
        json.dump(_response, handle)


def fetch_providers(providers_urls: Union[str, List[str]] = None) -> list:
    """Fetch OPTIMADE database providers (from Materials-Consortia)

    :param providers_urls: String pr list of strings with versioned base URL(s)
        to Materials-Consortia providers database
    """
    if providers_urls and not isinstance(providers_urls, (list, str)):
        raise TypeError("providers_urls must be a string or list of strings")

    if not providers_urls:
        providers_urls = PROVIDERS_URLS
    elif not isinstance(providers_urls, list):
        providers_urls = [providers_urls]

    for providers_url in providers_urls:
        providers = perform_optimade_query(base_url=providers_url, endpoint="")
        msg, _ = handle_errors(providers)
        if msg:
            LOGGER.warning("%r returned error(s).", providers_url)
        else:
            break
    else:
        if CACHED_PROVIDERS.exists():
            # Load local cached providers file
            LOGGER.warning(
                "Loading local, possibly outdated, list of providers (%r).",
                CACHED_PROVIDERS.name,
            )
            with open(CACHED_PROVIDERS, "r") as handle:
                providers = json.load(handle)
        else:
            LOGGER.error(
                "Neither any of the provider URLs: %r returned a valid response, "
                "and the local cached file of the latest valid response does not exist.",
                providers_urls,
            )
            providers = {}

    update_local_providers_json(providers)
    return providers.get("data", [])


VERSION_PARTS = []
for ver in __optimade_version__:
    VERSION_PARTS.extend(
        [
            f"/v{ver.split('-')[0].split('+')[0].split('.')[0]}",  # major
            f"/v{'.'.join(ver.split('-')[0].split('+')[0].split('.')[:2])}",  # major.minor
            f"/v{'.'.join(ver.split('-')[0].split('+')[0].split('.')[:3])}",  # major.minor.patch
        ]
    )
VERSION_PARTS = sorted(set(VERSION_PARTS), reverse=True)
LOGGER.debug("All known version editions: %s", VERSION_PARTS)


def get_versioned_base_url(  # pylint: disable=too-many-branches
    base_url: Union[str, dict, Link, AnyUrl]
) -> str:
    """Retrieve the versioned base URL

    First, check if the given base URL is already a versioned base URL.

    Then, use `Version Negotiation` as outlined in the specification:
    https://github.com/Materials-Consortia/OPTIMADE/blob/v1.0.0/optimade.rst#version-negotiation

    1. Try unversioned base URL's `/versions` endpoint.
    2. Go through valid versioned base URLs.

    """
    if isinstance(base_url, dict):
        base_url = base_url.get("href", "")
    elif isinstance(base_url, Link):
        base_url = base_url.href

    LOGGER.debug("Retrieving versioned base URL for %r", base_url)

    for version in VERSION_PARTS:
        if version in base_url:
            if re.match(fr".+{version}$", base_url):
                return base_url
            if re.match(fr".+{version}/$", base_url):
                return base_url[:-1]
            LOGGER.debug(
                "Found version '%s' in base URL '%s', but not at the end of it. Will continue.",
                version,
                base_url,
            )

    # 1. Try unversioned base URL's `/versions` endpoint.
    versions_endpoint = (
        f"{base_url}versions" if base_url.endswith("/") else f"{base_url}/versions"
    )
    try:
        response = SESSION.get(versions_endpoint, timeout=TIMEOUT_SECONDS)
        if response.from_cache:
            LOGGER.debug("Request to %s was taken from cache !", versions_endpoint)
    except (
        requests.exceptions.ConnectTimeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.ReadTimeout,
    ):
        pass
    else:
        if response.status_code == 200:
            # This endpoint should be of type "text/csv"
            csv_data = response.text.splitlines()
            keys = csv_data.pop(0).split(",")
            versions = {}.fromkeys(keys, [])
            for line in csv_data:
                values = line.split(",")
                for key, value in zip(keys, values):
                    versions[key].append(value)

            if versions.get("version", []):
                for version in versions:
                    version_path = f"/v{version}"
                    if version_path in VERSION_PARTS:
                        LOGGER.debug(
                            "Found versioned base URL through /versions endpoint."
                        )
                        return (
                            base_url + version_path[1:]
                            if base_url.endswith("/")
                            else base_url + version_path
                        )

    timeout_seconds = 5  # Use custom timeout seconds due to potentially many requests

    # 2. Go through valid versioned base URLs.
    for version in VERSION_PARTS:
        versioned_base_url = (
            base_url + version[1:] if base_url.endswith("/") else base_url + version
        )
        try:
            response = SESSION.get(
                f"{versioned_base_url}/info", timeout=timeout_seconds
            )
            if response.from_cache:
                LOGGER.debug(
                    "Request to %s/info was taken from cache !", versioned_base_url
                )
        except (
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.ReadTimeout,
        ):
            continue
        else:
            if response.status_code == 200:
                LOGGER.debug(
                    "Found versioned base URL through adding valid versions to path and requesting "
                    "the /info endpoint."
                )
                return versioned_base_url

    return ""


def get_list_of_valid_providers() -> Tuple[
    List[Tuple[str, LinksResourceAttributes]], List[str]
]:
    """Get curated list of database providers

    Return formatted list of tuples to use with a dropdown-widget.
    """
    providers = fetch_providers()
    res = []
    invalid_providers = []

    for entry in providers:
        provider = LinksResource(**entry)

        # Skip if "exmpl", "optimade" or "aiida"
        if provider.id in ["exmpl", "optimade", "aiida"]:
            LOGGER.debug("Skipping provider: %s", provider)
            continue

        attributes = provider.attributes

        # NOTE: Temporarily disable providers NOT properly satisfying the OPTIMADE specification
        # Follow issue #206: https://github.com/CasperWA/voila-optimade-client/issues/206
        # For omdb: Follow issue #246: https://github.com/CasperWA/voila-optimade-client/issues/246
        temp_disable_providers = ["cod", "tcod", "nmd", "omdb", "oqmd"]
        if provider.id in temp_disable_providers:
            LOGGER.debug("Temporarily disabling provider: %s", str(provider))
            invalid_providers.append((attributes.name, attributes))
            continue

        # Skip if not an 'external' link_type database
        if attributes.link_type != LinkType.EXTERNAL:
            LOGGER.debug(
                "Skip %s: Links resource not an %r link_type, instead: %r",
                attributes.name,
                LinkType.EXTERNAL,
                attributes.link_type,
            )
            continue

        # Disable if there is no base URL
        if attributes.base_url is None:
            LOGGER.debug("Base URL found to be None for provider: %s", str(provider))
            invalid_providers.append((attributes.name, attributes))
            continue

        versioned_base_url = get_versioned_base_url(attributes.base_url)
        if versioned_base_url:
            attributes.base_url = versioned_base_url
        else:
            # Not a valid/supported provider: skip
            LOGGER.debug(
                "Could not determine versioned base URL for provider: %s", str(provider)
            )
            invalid_providers.append((attributes.name, attributes))
            continue

        res.append((attributes.name, attributes))

    return res + invalid_providers, [name for name, _ in invalid_providers]


def validate_api_version(version: str, raise_on_fail: bool = True) -> str:
    """Given an OPTIMADE API version, validate it against current supported API version"""
    if not version:
        msg = (
            "No version found in response. "
            f"Should have been one of {', '.join(['v' + _ for _ in __optimade_version__])}"
        )
        if raise_on_fail:
            raise ApiVersionError(msg)
        return msg

    if version.startswith("v"):
        version = version[1:]

    if version not in __optimade_version__:
        msg = (
            f"Only OPTIMADE {', '.join(['v' + _ for _ in __optimade_version__])} are supported. "
            f"Chosen implementation has v{version}"
        )
        if raise_on_fail:
            raise ApiVersionError(msg)
        return msg

    return ""


def get_entry_endpoint_schema(base_url: str, endpoint: str = None) -> dict:
    """Retrieve provider's entry endpoint schema (default: /structures)."""
    result = {}

    endpoint = endpoint if endpoint is not None else "structures"
    endpoint = f"/info/{endpoint.strip('/')}"

    response = perform_optimade_query(endpoint=endpoint, base_url=base_url)
    msg, _ = handle_errors(response)
    if msg:
        LOGGER.error(
            "Could not retrieve information about entry-endpoint %r.\n  Message: %r\n  Response:"
            "\n%s",
            endpoint[len("/info/") :],
            msg,
            response,
        )
        return result

    return response.get("data", {}).get("properties", {})


def get_sortable_fields(base_url: str, endpoint: str = None) -> List[str]:
    """Retrieve sortable fields for entry endpoint (default: /structures)."""
    endpoint = endpoint if endpoint is not None else "structures"

    schema = get_entry_endpoint_schema(base_url, endpoint)

    return [field for field in schema if schema[field].get("sortable", False)]


def handle_errors(response: dict) -> Tuple[str, set]:
    """Handle any errors"""
    if "data" not in response and "errors" not in response:
        raise InputError(f"No data and no errors reported in response: {response}")

    if "errors" in response:
        LOGGER.error("Errored response:\n%s", json.dumps(response, indent=2))

        if "data" in response:
            msg = (
                '<font color="red">Error(s) during querying,</font> but '
                f"<strong>{len(response['data'])}</strong> structures found."
            )
        elif isinstance(response["errors"], dict) and "detail" in response["errors"]:
            msg = (
                '<font color="red">Error(s) during querying. '
                f"Message from server:<br>{response['errors']['detail']!r}.</font>"
            )
        elif isinstance(response["errors"], list) and any(
            ["detail" in _ for _ in response["errors"]]
        ):
            details = [_["detail"] for _ in response["errors"] if "detail" in _]
            msg = (
                '<font color="red">Error(s) during querying. Message(s) from server:<br> - '
                f"{'<br> - '.join(details)!r}</font>"
            )
        else:
            msg = (
                '<font color="red">Error during querying, '
                "please try again later.</font>"
            )

        http_errors = set()
        for raw_error in response.get("errors", []):
            try:
                error = OptimadeError(**raw_error)
                status = int(error.status)
            except (ValidationError, TypeError, ValueError):
                status = 400
            http_errors.add(status)

        return msg, http_errors

    return "", set()


def check_entry_properties(
    base_url: str,
    entry_endpoint: str,
    properties: Union[str, Iterable[str]],
    checks: Union[str, Iterable[str]],
) -> List[str]:
    """Check an entry-endpoint's properties

    :param checks: An iterable, which only recognizes the following str entries:
    "sort", "sortable", "present", "queryable"
    The first two and latter two represent the same thing, i.e., whether a property is sortable
    and whether a property is present in the entry-endpoint's resource's attributes, respsectively.
    :param properties: Can be either a list or not of properties to check.
    :param entry_endpoint: A valid entry-endpoint for the OPTIMADE implementation,
    e.g., "structures", "_exmpl_calculations", or "/extensions/structures".
    """
    if isinstance(properties, str):
        properties = [properties]
    properties = list(properties)

    if not checks:
        # Don't make any queries if called improperly (with empty iterable for `checks`)
        return properties

    if isinstance(checks, str):
        checks = [checks]
    checks = set(checks)
    if "queryable" in checks:
        checks.update({"present"})
        checks.remove("queryable")
    if "sortable" in checks:
        checks.update({"sort"})
        checks.remove("sortable")

    query_params = {
        "endpoint": f"/info/{entry_endpoint.strip('/')}",
        "base_url": base_url,
    }

    response = perform_optimade_query(**query_params)
    msg, _ = handle_errors(response)
    if msg:
        LOGGER.error(
            "Could not retrieve information about entry-endpoint %r.\n  Message: %r\n  Response:"
            "\n%s",
            entry_endpoint,
            msg,
            response,
        )
        if "present" in checks:
            return []
        return properties

    res = list(properties)  # Copy of input list of properties

    found_properties = response.get("data", {}).get("properties", {})
    for field in properties:
        field_property = found_properties.get(field, None)
        if field_property is None:
            LOGGER.debug(
                "Could not find %r in %r for provider with base URL %r. Found properties:\n%s",
                field,
                query_params["endpoint"],
                base_url,
                json.dumps(found_properties),
            )
            if "present" in checks:
                res.remove(field)
        elif "sort" in checks:
            sortable = field_property.get("sortable", False)
            if not sortable:
                res.remove(field)

    LOGGER.debug(
        "sortable fields found for %s (looking for %r): %r", base_url, properties, res
    )
    return res


def update_old_links_resources(resource: dict) -> Union[LinksResource, None]:
    """Try to update to resource to newest LinksResource schema"""
    try:
        res = LinksResource(**resource)
    except ValidationError:
        LOGGER.debug(
            "Links resource could not be cast to newest LinksResource model. Resource: %s",
            resource,
        )

        resource["attributes"]["link_type"] = resource["type"]
        resource["type"] = "links"

        LOGGER.debug(
            "Trying casting to LinksResource again with the updated resource: %s",
            resource,
        )
        try:
            res = LinksResource(**resource)
        except ValidationError:
            LOGGER.debug(
                "After updating 'type' and 'attributes.link_type' in resource, "
                "it still fails to cast to LinksResource model. Resource: %s",
                resource,
            )
            return None
        else:
            return res
    else:
        return res


def ordered_query_url(url: str) -> str:
    """Decode URL, sort queries, re-encode URL"""
    LOGGER.debug("Ordering URL: %s", url)
    parsed_url = urlparse(url)
    queries = parse_qs(parsed_url.query)
    LOGGER.debug("Queries to sort and order: %s", queries)

    sorted_keys = sorted(queries.keys())

    res = OrderedDict()
    for key in sorted_keys:
        # Since the values are all lists, we also sort these
        res[key] = sorted(queries[key])

    res = urlencode(res, doseq=True)
    res = (
        f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path};{parsed_url.params}?{res}"
        f"#{parsed_url.fragment}"
    )
    LOGGER.debug("Newly ordered URL: %s", res)
    LOGGER.debug("Treated URL after unparse(parse): %s", urlunparse(urlparse(res)))
    return urlunparse(urlparse(res))
