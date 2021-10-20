#!/usr/bin/env bash
set -e

echo -e "\n### Setting commit user ###"
git config --local user.email "${GIT_USER_EMAIL}"
git config --local user.name "${GIT_USER_NAME}"

echo -e "\n### Update version ###"
invoke update-version --version="${GITHUB_REF#refs/tags/}"

echo -e "\n### Commit updated files ###"
git commit -am "Release ${GITHUB_REF#refs/tags/}"

echo -e "\n### Update new version tag ###"
TAG_MSG=.github/utils/release_tag_msg.txt
sed -i "s|TAG_NAME|${GITHUB_REF#refs/tags/}|g" "${TAG_MSG}"
git tag -af -F "${TAG_MSG}" ${GITHUB_REF#refs/tags/}
