#!/bin/sh

# https://github.com/profusion/sgqlc/blob/fbee55d92554dd209b4e3ebda093f371bbc12aca/examples/github/update-schema.sh
# https://sgqlc.readthedocs.io/en/latest/sgqlc.codegen.html#generating-schema-types

if [ "${NO_DOWNLOAD}" != 1 ]; then
    if [ -z "${GH_TOKEN}" ]; then
        echo "please export GH_TOKEN with your GitHub API token" >&2
        echo "see: https://github.com/settings/tokens" >&2
        exit 1
    fi

    python3 \
        -m sgqlc.introspection \
        --exclude-deprecated \
        -H "Authorization: bearer ${GH_TOKEN}" \
        https://api.github.com/graphql \
        github_schema.json || exit 1
fi

sgqlc-codegen schema --docstrings github_schema.json github_schema.py || exit 1

python3 -c 'import github_schema' || exit 1
