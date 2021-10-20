#!/usr/bin/env bash
set -e

echo -e "\n### Setting commit user ###"
git config --local user.email "casper.andersen@epfl.ch"
git config --local user.name "CasperWA"

echo -e "\n### Install invoke ###"
pip install -U invoke

echo -e "\n### Update version ###"
invoke update-version --version="${GITHUB_REF#refs/tags/}"

echo -e "\n### Commit updated files ###"
git commit -am "Release ${GITHUB_REF#refs/tags/}"

echo -e "\n### Update new version tag ###"
TAG_MSG=.github/utils/release_tag_msg.txt
sed -i "s|TAG_NAME|${GITHUB_REF#refs/tags/}|g" "${TAG_MSG}"
git tag -af -F "${TAG_MSG}" ${GITHUB_REF#refs/tags/}
