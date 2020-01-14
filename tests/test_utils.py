import pytest

from aiidalab_optimade import exceptions as exc
from aiidalab_optimade import utils


def test_fetch_providers_wrong_url():
    """Test when fetch_providers is provided a wrong URL"""
    wrong_url = "https://this.is.a.wrong.url"

    with pytest.raises(exc.NonExistent):
        utils.fetch_providers(providers_url=wrong_url)


def test_fetch_providers_content():
    """Test known content in dict of database providers"""
    exmpl = {
        "type": "provider",
        "id": "exmpl",
        "attributes": {
            "name": "Example provider",
            "description": "Provider used for examples, not to be assigned to a real database",
            "base_url": "https://example.com/optimade",
            "homepage": "https://example.com",
        },
    }

    assert exmpl in utils.fetch_providers()


def test_validate_provider_details():
    """Test empty strings are returned if None values are found"""
    none_details = {
        "description": None,
        "base_url": None,
        "homepage": None,
        "name": None,
    }

    res = utils.validate_provider_details(none_details)

    # Make sure the size of the dict is still the same
    assert len(res) == len(none_details)

    # Make sure all None values are now empty strings
    for value in res.values():
        assert value == ""

    # Test that if it is run through again, it does not change the values
    for value in utils.validate_provider_details(res).values():
        assert value == ""

    # Make sure InputError is raised when a None input is given
    with pytest.raises(exc.InputError):
        utils.validate_provider_details(None)


def test_exmpl_not_in_list():
    """Make sure the 'exmpl' database provider is not in the final list"""
    exmpl = (
        "Example provider",
        {
            "description": "Provider used for examples, not to be assigned to a real database",
            "base_url": "https://example.com/index/optimade",
            "homepage": "https://example.com",
        },
    )

    materials_cloud = (
        "Materials Cloud",
        {
            "description": "Materials Cloud: A platform for Open Science built for seamless "
            "sharing of resources in computational materials science",
            "base_url": "https://www.materialscloud.org/optimade",
            "homepage": "https://www.materialscloud.org",
        },
    )

    list_of_database_providers = utils.get_list_of_valid_providers()

    assert exmpl not in list_of_database_providers
    assert materials_cloud in list_of_database_providers
