# The lists are set based on the status of providers from https://www.optimade.org/providers-dashboard/.
# If the provider has no databases attached, it is put into SKIP_PROVIDERS list means that the optimate-client will not support it.
# Otherwise put in DISABLE_PROVIDERS means the client need to be supported but can't because of issues.

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
