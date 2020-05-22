#!/bin/bash

# Rename jupyter_config.json to voila.json and copy it Jupyter's config dir
jupyter_config_dir=$(jupyter --config-dir)
cp -f ./jupyter_config.json "${jupyter_config_dir}/voila.json"

# Update sub-module
git submodule init
git submodule update

# Copy template to Jupyter data dir
./copy_voila_template.py materialscloud

# Start the tornado voila server (no browser)
voila --no-browser OPTIMADE_general.ipynb
