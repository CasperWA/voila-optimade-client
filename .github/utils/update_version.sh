#!/usr/bin/env bash
set -e

echo -e "\n### Setting commit user ###"
git config --local user.email "${GIT_USER_EMAIL}"
git config --local user.name "${GIT_USER_NAME}"

echo -e "\n### Update version ###"
invoke update-version --version="${GITHUB_REF#refs/tags/}"

echo -e "\n### Commit updated files ###"
git add optimade_client/__init__.py setup.py optimade_client/informational.py optimade_client/cli/run.py
git add CHANGELOG.md
git commit -m "Release ${GITHUB_REF#refs/tags/}"

echo -e "\n### Update new version tag ###"
TAG_MSG=.github/utils/release_tag_msg.txt
sed -i "s|TAG_NAME|${GITHUB_REF#refs/tags/}|g" "${TAG_MSG}"
git tag -af -F "${TAG_MSG}" ${GITHUB_REF#refs/tags/}
