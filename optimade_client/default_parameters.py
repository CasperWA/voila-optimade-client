"""Default initialization parameters

The lists are set, based on the status of providers from
https://www.optimade.org/providers-dashboard/.

If the provider has no available databases, it should be put into the SKIP_PROVIDERS list,
meaning it will not be supported.
Providers in the DISABLE_PROVIDERS list are ones the client should support,
but cannot because of one issue or another.
"""

SKIP_PROVIDERS = [
    "exmpl",
    "optimade",
    "aiida",
    "ccpnc",
    "matcloud",
    "necro",
    "httk",
    "pcod",
]

DISABLE_PROVIDERS = [
    "cod",
    "tcod",
    "nmd",
    "oqmd",
    "aflow",
    "mpds",
    "jarvis",
]

PROVIDER_DATABASE_GROUPINGS = {
    "Materials Cloud": {
        "Main Projects": ["mc3d", "mc2d"],
        "Contributed Projects": [
            "2dtopo",
            "pyrene-mofs",
            "scdm",
            "stoceriaitf",
            "tc-applicability",
            "tin-antimony-sulfoiodide",
            "curated-cofs",
        ],
    }
}


SKIP_DATABASE = {
    "Materials Cloud": ["optimade-sample", "li-ion-conductors", "sssp"],
}
