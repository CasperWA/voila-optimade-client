from aiidalab_optimade import utils


def test_fetch_providers_wrong_url():
    """Test when fetch_providers is provided a wrong URL"""
    wrong_url = "https://this.is.a.wrong.url"

    providers = utils.fetch_providers(providers_url=wrong_url)
    assert providers == []


def test_fetch_providers_content():
    """Test known content in dict of database providers"""
    exmpl = {
        "type": "links",
        "id": "exmpl",
        "attributes": {
            "name": "Example provider",
            "description": "Provider used for examples, not to be assigned to a real database",
            "base_url": "http://providers.optimade.org/index-metadbs/exmpl",
            "homepage": "https://example.com",
            "link_type": "external",
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
            "link_type": "external",
        },
    )

    mcloud = (
        "Materials Cloud",
        {
            "name": "Materials Cloud",
            "description": "A platform for Open Science built for seamless "
            "sharing of resources in computational materials science",
            "base_url": "https://www.materialscloud.org/optimade/v0",
            "homepage": "https://www.materialscloud.org",
            "link_type": "external",
        },
    )

    odbx = (
        "open database of xtals",
        {
            "name": "open database of xtals",
            "description": "A public database of crystal structures mostly derived from ab initio "
            "structure prediction from the group of Dr Andrew Morris at the University of "
            "Birmingham https://ajm143.github.io",
            "base_url": "https://optimade.odbx.science/v0",
            "homepage": "https://odbx.science",
            "link_type": "external",
        },
    )

    list_of_database_providers = utils.get_list_of_valid_providers()

    assert exmpl not in list_of_database_providers
    assert mcloud in list_of_database_providers or odbx in list_of_database_providers
