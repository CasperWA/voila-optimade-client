import requests
from aiidalab_optimade import exceptions as exc

TIMEOUT_SECONDS = 30  # Seconds before timeout is raised

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
        raise exc.NonExistent("The URL cannot be opened: {}".format(providers_url))
    else:
        providers = providers.json()

    # Return list of providers
    return providers["data"]


def validate_provider_details(details: dict) -> dict:
    """Validate dict of details from providers.json"""
    if not details or not isinstance(details, dict):
        raise exc.InputError("Please specify 'details', it must be a dict")

    for field in details:
        if details[field] is None:
            details[field] = ""

    return details


def get_list_of_database_providers():
    """ Get list of database providers

    Return formatted list of tuples to use for a dropdown-widget.
    """
    providers = fetch_providers()
    res = []

    for provider in providers:
        # Skip if "exmpl"
        if provider["id"] == "exmpl":
            continue

        attributes = provider["attributes"]
        provider_name = attributes.pop("name")
        res.append((provider_name, attributes))

    return res
