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


def test_exmpl_not_in_list():
    """Make sure the 'exmpl' database provider is not in the final list"""
    exmpl = (
        "Example provider",
        {
            "name": "Example provider",
            "description": "Provider used for examples, not to be assigned to a real database",
            "base_url": "https://example.com/index/optimade",
            "homepage": "https://example.com",
        },
    )

    materials_cloud = (
        "Materials Cloud",
        {
            "name": "Materials Cloud",
            "description": "Materials Cloud: A platform for Open Science built for seamless "
            "sharing of resources in computational materials science",
            "base_url": "https://www.materialscloud.org/optimade/v0",
            "homepage": "https://www.materialscloud.org",
        },
    )

    list_of_database_providers = utils.get_list_of_valid_providers()

    assert exmpl not in list_of_database_providers
    assert materials_cloud in list_of_database_providers
