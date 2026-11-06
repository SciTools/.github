# Scripted Eterna Sprint board refresh

## What is the Eterna Sprint board?

A GitHub Project ("sprint board" style) that tracks Issues and Pull Requests
across the same repos as [Peloton](../peloton). Unlike Peloton, it has **one**
List view sliced by Repository, plus a cross-repo Kanban view of items whose
`Status` field has been manually set to "active" by the team - the script
never touches `Status`, that is a purely manual, drag-the-card action.

## Help! The board is out of date!

Follow all steps in
[How to refresh the board manually](#how-to-refresh-the-board-manually).

## How the board is refreshed

The [sgqlc](https://github.com/profusion/sgqlc) library provides a Pythonic
interface to [GitHub's GraphQL API](https://docs.github.com/en/graphql) - the
primary way of interacting with GitHub programmatically.
[`update_project.py`](update_project.py) uses sgqlc to query GitHub
issues/PRs, then uses sgqlc to add newly-matching items to the project and
remove items that no longer match (e.g. closed long ago). This is usually run
automatically by
[this GitHub Action](../.github/workflows/eterna-sprint.yml).

Unlike [Peloton](../peloton), this script does **not** push any field values
into the project - it only adds/removes items. All other fields (including
`Status`) are configured and maintained manually in the GitHub UI; see
[`project_settings.md`](project_settings.md).

## How to refresh the board manually

### Generate a GitHub access token

Performing backend automation with GitHub requires an access token with
appropriate permissions. Visit
[this page](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
for instructions on creating your own.

The token must have the following scopes to enable running all refresh
operations:

- All `repo` scopes
- `admin:org > read:org`
- `project > read:project`

(For the GitHub Action: a token is generated on-the-fly by the `scitools-ci`
GitHub App, via the
[`tibdex/github-app-token` action](https://github.com/tibdex/github-app-token).
See [the GitHub Action](../.github/workflows/eterna-sprint.yml) for more.)

### Set up an environment

Run all scripts in an environment that contains the packages listed
in [`requirements.txt`](requirements.txt).

### Run the refresh script

**It is important to try this first**, to check whether you can replicate any
problems observed on the GitHub Action.

```shell
python update_project.py --bearer_token <your_github_access_token>
```

See also `python update_project.py --help` for more options.

Output will be written to `latest_eterna_sprint_update.log`.

### Debugging

1. Try reducing the `_PAGINATION` numbers in
[`update_project.py`](update_project.py) to see if the script is failing due
to rate limiting or timeouts.
1. Try [Updating the Python schema](#updating-the-python-schema).
1. Further troubleshooting will be case-by-case.

### Updating the Python 'schema'

Use [`update-schema.sh`](update-schema.sh) to convert the latest GitHub
GraphQL schema into Python classes; you will need your GitHub
token to run this. Note that the script produces both a JSON and a Python
file, but only the Python file ([`github_schema.py`](github_schema.py)) is
under source control - the JSON file is not used. This Python 'schema' is a
very large file, and we do **not** vet its contents.
