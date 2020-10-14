#!/usr/bin/env bash
set -e

if [ -n "${CI}" ]; then
    echo "Not checking codecov configuration file when CI is true."
    exit 0
fi

CODECOV_FILE=.codecov.yml

curl -s --data-binary @${CODECOV_FILE} https://codecov.io/validate | grep Valid! || ( curl -s --data-binary @${CODECOV_FILE} https://codecov.io/validate ; exit 1)
