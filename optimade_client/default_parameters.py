# Check https://www.optimade.org/providers-dashboard/
# If provider has no DB attached put into SKIP_PROVIDERS means not
# going to support it at the moment.
# Otherwise put in DISABLE_PROVIDERS means the client need to support
# it but has issue to serve the data.
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
