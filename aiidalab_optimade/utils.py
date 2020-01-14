import json
from six.moves.urllib.request import urlopen
from aiidalab_optimade import exceptions as exc

TIMEOUT_SECONDS = 30  # Seconds before timeout is raised

TEMP_PROVIDERS_URL = "https://raw.githubusercontent.com/Materials-Consortia/OPTiMaDe/247aa7bfa7d260719297d5889a2844bdddd5d4bc/providers.json"


def fetch_providers(providers_url=None):
    """ Fetch OPTiMaDe database providers
    Fetch JSON file from GitHub.com/Materials-Consortia/OPTiMaDe/providers.json
    :param providers_url: String with URL to providers.json file
    """
    if providers_url and not isinstance(providers_url, str):
        raise TypeError("providers_url must be a string")

    if not providers_url:
        providers_url = TEMP_PROVIDERS_URL

    try:
        providers = urlopen(providers_url, timeout=TIMEOUT_SECONDS)
        providers = providers.read()
    except Exception:
        raise exc.NonExistent("The URL cannot be opened: {}".format(providers_url))

    # Load providers.json
    providers = json.loads(providers)

    # Get dict of providers
    providers = providers["data"][0]["attributes"]["providers"]

    return providers


def validate_provider_details(details):
    """Validate dict of details from providers.json"""
    from string import capwords

    if not details or not isinstance(details, dict):
        raise exc.InputError("Please specify 'details', it must be a dict")

    if details["index_base_url"] is None:
        details["index_base_url"] = ""

    if details["description"] is None:
        details["description"] = ""

    details["description"] = capwords(details["description"])

    return details


def get_list_of_database_providers():
    """ Get list of database providers
    Return formatted list of tuples to use for a dropdown-widget.
    """
    # Fetch providers from official providers.json
    providers_dict = fetch_providers()

    # Initialize
    res = []

    # Go through dict of providers
    for provider, details in providers_dict.items():
        # Skip if "exmpl"
        if provider == "exmpl":
            continue

        # Validate details
        details = validate_provider_details(details)

        res_dict = {}
        res_dict["name"] = provider
        res_dict["index"] = details["index_base_url"]

        provider_name = details["description"]

        res.append((provider_name, res_dict))

    return res
