#!/bin/sh
set -e

echo "\n### Checkout fresh branch ###"
git checkout -b update_version

echo "\n### Setting commit user ###"
git config --local user.email "casper.andersen@epfl.ch"
git config --local user.name "CasperWA"

echo "\n### Install invoke ###"
pip install -U invoke

echo "\n### Update version ###"
invoke update-version --version="${GITHUB_REF#refs/tags/}"

echo "\n### Commit updated files ###"
git add setup.py
git add optimade_client/__init__.py
git add optimade_client/informational.py
git commit -m "Release ${GITHUB_REF#refs/tags/}"
