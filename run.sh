#!/bin/bash

# Rename jupyter_config.json to voila.json and copy it Jupyter's config dir
jupyter_config_dir=$(jupyter --config-dir)
cp -f ./jupyter_config.json "${jupyter_config_dir}/voila.json"

if [ "$1" == "debug" ]; then
    echo "Starting in DEBUG mode !"
    export OPTIMADE_CLIENT_DEBUG=True
else
    OPTIMADE_CLIENT_DEBUG=
fi

# Update sub-module
git submodule init
git submodule update

# Copy template to Jupyter data dir
./copy_voila_template.py materialscloud

# Start the tornado voila server (no browser)
voila --no-browser "OPTIMADE Client.ipynb"
