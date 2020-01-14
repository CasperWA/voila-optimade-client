import pytest

from .. import utils
from .. import exceptions as exc


def test_fetch_providers_wrong_url():
    """Test when fetch_providers is provided a wrong URL"""
    WRONG_URL = "https://this.is.a.wrong.url"

    with pytest.raises(exc.NonExistent):
        utils.fetch_providers(providers_url=WRONG_URL)


def test_fetch_providers_content():
    """Test known content in dict of database providers"""
    EXMPL = (
        "exmpl",
        {
            "description": "used for examples, not to be assigned to a real database",
            "index_base_url": "http://example.com/optimade/index/",
        },
    )

    assert EXMPL[0], EXMPL[1] in list(utils.fetch_providers().items())


def test_validate_provider_details():
    """Test empty strings are returned if None values are found"""
    NONE_DETAILS = {"description": None, "index_base_url": None}

    res = utils.validate_provider_details(NONE_DETAILS)

    # Make sure the size of the dict is still the same
    assert len(res) == len(NONE_DETAILS)

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
    """Test the 'exmpl' database provider is not in the final list"""
    from string import capwords

    EXMPL = (
        capwords("used for examples, not to be assigned to a real database"),
        {"name": "exmpl", "index": "http://example.com/optimade/index/"},
    )

    MAT_CLOUD = (capwords("materialscloud.org"), {"name": "mcloud", "index": ""})

    list_of_database_providers = utils.get_list_of_database_providers()

    assert EXMPL not in list_of_database_providers
    assert MAT_CLOUD in list_of_database_providers
