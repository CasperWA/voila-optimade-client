#!/bin/bash

# Rename jupyter_config.json to voila.json and copy it Jupyter's config dir
jupyter_config_dir=$(jupyter --config-dir)
cp -f ./jupyter_config.json "${jupyter_config_dir}/voila.json"

# Start the tornado voila server (no browser)
voila --no-browser OPTIMADE_general.ipynb
