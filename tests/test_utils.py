from optimade_client import utils


def test_fetch_providers_wrong_url():
    """Test when fetch_providers is provided a wrong URL

    It should now return at the very least the cached list of providers
    """
    import json

    wrong_url = "https://this.is.a.wrong.url"

    providers = utils.fetch_providers(providers_urls=wrong_url)
    if utils.CACHED_PROVIDERS.exists():
        with open(utils.CACHED_PROVIDERS, "r") as handle:
            providers_file = json.load(handle)
        assert providers == providers_file.get("data", [])
    else:
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
    from optimade.models import LinksResourceAttributes

    exmpl = (
        "Example provider",
        LinksResourceAttributes(
            **{
                "name": "Example provider",
                "description": "Provider used for examples, not to be assigned to a real database",
                "base_url": "https://example.com/index/optimade",
                "homepage": "https://example.com",
                "link_type": "external",
            }
        ),
    )

    mcloud = (
        "Materials Cloud",
        LinksResourceAttributes(
            **{
                "name": "Materials Cloud",
                "description": "A platform for Open Science built for seamless "
                "sharing of resources in computational materials science",
                "base_url": "https://www.materialscloud.org/optimade/v1.0.0",
                "homepage": "https://www.materialscloud.org",
                "link_type": "external",
            }
        ),
    )

    odbx = (
        "open database of xtals",
        LinksResourceAttributes(
            **{
                "name": "open database of xtals",
                "description": "A public database of crystal structures mostly derived from ab "
                "initio structure prediction from the group of Dr Andrew Morris at the University "
                "of Birmingham https://ajm143.github.io",
                "base_url": "https://optimade.odbx.science/v1.0.0",
                "homepage": "https://odbx.science",
                "link_type": "external",
            }
        ),
    )

    list_of_database_providers = utils.get_list_of_valid_providers()

    assert exmpl not in list_of_database_providers
    assert mcloud in list_of_database_providers or odbx in list_of_database_providers


def test_ordered_query_url():
    """Check ordered_query_url().

    Testing already sorted URLs, making sure they come out exactly the same as when they came in.
    """
    normal_url = (
        "https://optimade.materialsproject.org/v1.0.0/structures?filter=%28+nelements%3E%3D1+AND+"
        "nelements%3C%3D9+AND+nsites%3E%3D1+AND+nsites%3C%3D444+%29+AND+%28+NOT+structure_features"
        "+HAS+ANY+%22assemblies%22+%29&page_limit=10&page_number=1&page_offset=30&response_format"
        "=json"
    )
    multi_query_param_url = (
        "https://optimade.materialsproject.org/v1.0.0/structures?filter=%28+nelements%3E%3D1+AND+"
        "nelements%3C%3D9+AND+nsites%3E%3D1+AND+nsites%3C%3D444+%29+AND+%28+NOT+structure_features"
        "+HAS+ANY+%22assemblies%22+%29&page_limit=10&page_number=1&page_offset=30&response_format"
        "=json&response_format=xml"
    )

    ordered_url = utils.ordered_query_url(normal_url)
    assert ordered_url == normal_url

    ordered_url = utils.ordered_query_url(multi_query_param_url)
    assert ordered_url == multi_query_param_url
