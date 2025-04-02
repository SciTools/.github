# Templating

SciTools developers manage several similar repositories. Where the same files
are used across multiple repositories, it helps to keep them as similar as
possible. We achieve this by storing templates for common files in this
directory.

## Benefits

- Smoother transition for developers when switching between repositories.
- Encodes agreed SciTools best practices.
- Avoids useful ideas being isolated to the repository where they were first 
tried. 
- A way to share simple scripting across repositories without needing an
installable package or similar - less overhead and easier to follow.

## How it works

[`_templating_include.json`](_templating_include.json) is the 'index' of all the
templates and how they map to files in the SciTools repositories.

[`_templating_exclude.json`](_templating_exclude.json) is the 'index' of all the
files that are found in commonly templated directories within the SciTools repositories,
but that we do not wish to template.

[`_templating_scripting.py`](_templating_scripting.py) contains the logic for
communicating template updates around SciTools - using GitHub issues and
comments. It is called by two GitHub Actions workflows:

- [`template-update-notification.yml`](../.github/workflows/template-update-notification.yml)
uses the `notify_updates()` function to raise issues on all relevant
repositories when a template is updated, or a new one created.
- [SciTools/workflows `ci-template-check.yml`](https://github.com/SciTools/workflows/blob/main/.github/workflows/ci-template-check.yml)
uses the `prompt_share()` function to remind repository developers if they are
modifying a templated file and should consider sharing the change.

All other files in this directory are the templates themselves.

## Things we template

- Files that all repositories should have, e.g. `CODE_OF_CONDUCT.md`.
- Tools that will be valuable to multiple repositories, e.g. benchmarking
scripts.
- Files that are useful to have in a consistent format, e.g. 
`.pre-commit-config.yaml`.

Files DO NOT need to be identical - they are human-readable not 
machine-readable, so can include whatever placeholders / optional content is
considered appropriate.

## Please contribute!

This directory needs to grow. Any files you can think to template will be a 
valuable addition.
**Remember to update [`_templating_include.json`](_templating_include.json).**

