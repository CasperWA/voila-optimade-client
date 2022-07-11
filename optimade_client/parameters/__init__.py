PROVIDER_DATABASE_GROUPINGS = {
    "Materials Cloud": {
        "Main Projects": ["mc3d-structures", "2dstructures"],
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
    "Materials Cloud": ["optimade-sample", "li-ion-conductors", "threedd", "sssp"],
}

SKIP_PROVIDERS = ["exmpl", "optimade", "aiida", "ccpnc"]

DISABLE_PROVIDERS = [
    "cod",
    "tcod",
    "nmd",
    "oqmd",
    "aflow",
    "matcloud",
    "mpds",
    "necro",
    "jarvis",
]
