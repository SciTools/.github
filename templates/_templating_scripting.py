#!/usr/bin/env python3
"""Commands and scripts for administrating templating of files across SciTools repos.
"""
import argparse
import json
from pathlib import Path
import shlex
from subprocess import CalledProcessError, check_output, run
from tempfile import NamedTemporaryFile
from typing import NamedTuple


def git_command(command: str) -> str:
    command = shlex.split(f"git {command}")
    return check_output(command).decode("utf-8").strip()


GIT_ROOT = Path(git_command("rev-parse --show-toplevel")).resolve()
TEMPLATES_DIR = GIT_ROOT / "templates"
assert TEMPLATES_DIR.is_dir()


class Config:
    """Convenience to give the config JSON some readable structure."""
    class TargetRepo(NamedTuple):
        repo: str
        path_in_repo: Path

    def __init__(self):
        with (TEMPLATES_DIR / "_templating_config.json").open() as file_read:
            config = json.load(file_read)

        self.templates: dict[Path, list[Config.TargetRepo]] = {}

        for _template, _target_repos in config.items():
            template = TEMPLATES_DIR / _template
            assert template.is_file()
            target_repos = [
                Config.TargetRepo(repo=repo, path_in_repo=Path(file_path))
                for repo, file_path in _target_repos.items()
            ]
            self.templates[template] = target_repos


CONFIG = Config()


def notify_updates() -> None:
    # Create issues on repos that use templates that have been updated.
    def git_diff(*args: str) -> str:
        command = "diff HEAD^ HEAD " + " ".join(args)
        return git_command(command)

    diff_output = git_diff("--name-only")
    changed_files = [GIT_ROOT / line for line in diff_output.splitlines()]
    changed_templates = [
        file for file in changed_files if file.is_relative_to(TEMPLATES_DIR)
    ]

    scitools_url = "https://github.com/SciTools"

    for template in changed_templates:
        templatees = CONFIG.templates[template]

        diff = git_diff("--", str(template))
        issue_title = f"The Template for `{template.name}` has been updated"
        template_relative = template.relative_to(GIT_ROOT)
        template_url = (
            f"{scitools_url}/.github/blob/main/{template_relative}"
        )
        template_link = f"[`{template_relative}`]({template_url})"
        for repo, path_in_repo in templatees:
            file_url = f"{scitools_url}/{repo}/blob/main/{path_in_repo}"
            file_link = f"[`{path_in_repo}`]({file_url})"
            issue_body = (
                f"The template for {file_link} has been updated.\n\n"
                "Consider adopting these changes into the repo; "
                "the changes can be found below.\n\n"
                "The template file can be found in the **.github** repo: "
                f"{template_link}\n\n"
                "The diff between the specified file is as follows:\n\n"
                f"```diff\n{diff}\n```"
            )
            with NamedTemporaryFile("w") as file_write:
                file_write.write(issue_body)
                file_write.flush()
                gh_command = shlex.split(
                    "gh issue create "
                    f'--title "{issue_title}" '
                    f"--body-file {file_write.name} "
                    f"--repo SciTools/{repo} "
                    f'--label "Bot" '
                    f'--label "Type: Infrastructure" '
                )
                try:
                    run(gh_command, check=True, capture_output=True)
                except CalledProcessError as error:
                    # If a label doesn't exist, fall back on no labels (simpler
                    #  than trying/removing individual labels).
                    error_text = error.stderr.decode("utf-8")
                    if error_text.startswith("could not add label"):
                        labels_start = gh_command.index("--label")
                        gh_command = gh_command[:labels_start]
                        run(gh_command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="TemplatingScripting",
        description="Commands for administrating templating of files across SciTools repos."
    )
    subparsers = parser.add_subparsers(required=True)
    notify = subparsers.add_parser(
        "notify-updates",
        description="Create issues on repos that use templates that have been updated."
    )
    notify.set_defaults(func=notify_updates)
    # TODO: command to check templates/ dir aligns with _templating_config.json.
    #  Run this on PRs for the .github repo.
    # TODO: command to make PR authors - on templatee repos - that they are
    #  modifying a templated file.
    #   Run this on PRs for the templatee repos.

    parsed = parser.parse_args()
    parsed.func()


if __name__ == "__main__":
    main()
