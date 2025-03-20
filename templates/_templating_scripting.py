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
from urllib.parse import urlparse


SCITOOLS_URL = "https://github.com/SciTools"
TEMPLATES_DIR = Path(__file__).parent.resolve()
TEMPLATE_REPO_ROOT = TEMPLATES_DIR.parent


def git_command(command: str) -> str:
    command = shlex.split(f"git {command}")
    return check_output(command).decode("utf-8").strip()


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

    def find_template(self, repo: str, path_in_repo: Path) -> Path | None:
        flattened = [
            (template, target_repo.repo, target_repo.path_in_repo)
            for template, target_repos in self.templates.items()
            for target_repo in target_repos
        ]
        matches = [
            template
            for template, target_repo, target_path in flattened
            if target_repo == repo and target_path == path_in_repo
        ]
        # Assumption: any given file in a given repo will only be
        #  governed by a single template.
        assert len(matches) <= 1
        return matches[0] if matches else None


CONFIG = Config()


def notify_updates(args: argparse.Namespace) -> None:
    """Create issues on repos that use templates that have been updated.

    This function is intended for running on the .github repo.
    """
    # Always passed (by common code), but never used in this routine.
    _ = args

    def git_diff(*args: str) -> str:
        command = "diff HEAD^ HEAD " + " ".join(args)
        return git_command(command)

    git_root = Path(git_command("rev-parse --show-toplevel")).resolve()
    diff_output = git_diff("--name-only")
    changed_files = [git_root / line for line in diff_output.splitlines()]
    changed_templates = [
        file for file in changed_files if file.is_relative_to(TEMPLATES_DIR)
    ]

    for template in changed_templates:
        templatees = CONFIG.templates[template]

        diff = git_diff("--", str(template))
        issue_title = (
            f"The template for `{template.relative_to(TEMPLATES_DIR)}` "
            "has been updated"
        )
        template_relative = template.relative_to(TEMPLATE_REPO_ROOT)
        template_url = (
            f"{SCITOOLS_URL}/.github/blob/main/{template_relative}"
        )
        template_link = f"[`{template_relative}`]({template_url})"
        for repo, path_in_repo in templatees:
            file_url = f"{SCITOOLS_URL}/{repo}/blob/main/{path_in_repo}"
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
                    else:
                        raise


def prompt_share(args: argparse.Namespace) -> None:
    """Make a PR author aware that they are modifying a templated file.

    This function is intended for running on a PR on a 'target repo'.
    """
    def gh_json(sub_command: str, field: str) -> dict:
        command = shlex.split(f"gh {sub_command} --json {field}")
        return json.loads(check_output(command))

    pr_number = args.pr_number

    def split_github_url(url: str) -> tuple[str, str, str]:
        _, org, repo, _, ref = urlparse(url).path.split("/")
        return org, repo, ref

    def url_to_short_ref(url: str) -> str:
        org, repo, ref = split_github_url(url)
        return f"{org}/{repo}#{ref}"

    pr_url = gh_json(f"pr view {pr_number}", "url")["url"]
    pr_short_ref = url_to_short_ref(pr_url)
    pr_repo = split_github_url(pr_url)[1]

    author = gh_json(f"pr view {pr_number}", "author")["author"]["login"]

    changed_files = gh_json(f"pr view {pr_number}", "files")["files"]
    changed_paths = [Path(file["path"]) for file in changed_files]

    def create_issue(title: str, body: str) -> None:
        # Check that an issue with this title isn't already on the .github repo.
        existing_issues = gh_json(
            "issue list --state all --repo SciTools/.github", "title"
        )
        if any(issue["title"] == title for issue in existing_issues):
            return

        with NamedTemporaryFile("w") as file_write:
            file_write.write(body)
            file_write.flush()
            gh_command = shlex.split(
                "gh issue create "
                f'--title "{title}" '
                f"--body-file {file_write.name} "
                "--repo SciTools/.github "
                f"--assignee {author}"
            )
            issue_url = check_output(gh_command).decode("utf-8").strip()
        short_ref = url_to_short_ref(issue_url)
        review_body = f"Please see {short_ref}"
        gh_command = shlex.split(
            f'gh pr review {pr_number} --request-changes --body "{review_body}"'
        )
        run(gh_command, check=True)

    for changed_path in changed_paths:
        template = CONFIG.find_template(pr_repo, changed_path)
        is_templated = template is not None
        if is_templated:
            template_relative = template.relative_to(TEMPLATE_REPO_ROOT)
            template_url = (
                f"{SCITOOLS_URL}/.github/blob/main/{template_relative}"
            )
            template_link = f"[`{template_relative}`]({template_url})"

            issue_title = (
                f"Apply {pr_short_ref} `{changed_path}` improvements to "
                f"`{template_relative}`?"
            )

            issue_body = (
                f"{pr_short_ref} (by @{author}) includes changes to "
                f"`{changed_path}`. This file is templated by {template_link}. "
                "Please either:\n\n"
                "- Action this issue with a pull request applying the changes "
                f"to {template_link}.\n"
                "- Close this issue if the changes are not suitable for "
                "templating."
            )
            create_issue(issue_title, issue_body)
        else:
            # Check if the file is in 'highly templated' locations. If so, worth
            #  prompting the user anyway.

            # Remember: this is running in the context of a 'target repo', NOT
            #  the .github repo (where the templates live).
            git_root = Path(git_command("rev-parse --show-toplevel")).resolve()
            changed_parent = changed_path.parent.resolve()
            if changed_parent in (
                git_root,
                git_root / "benchmarks",
                git_root / "docs" / "src",
            ):
                issue_title = (
                    f"Share {pr_short_ref} `{changed_path}` improvements via "
                    f"templating?"
                )

                templates_relative = TEMPLATES_DIR.relative_to(TEMPLATE_REPO_ROOT)
                templates_url = f"{SCITOOLS_URL}/.github/tree/main/{templates_relative}"
                templates_link = f"[`{templates_relative}/`]({templates_url})"
                issue_body = (
                    f"{pr_short_ref} (by @{author}) includes changes to "
                    f"`{changed_path}`. This file is not currently templated, "
                    "but its parent directory suggests it may be a good "
                    "candidate. Please either:\n\n"
                    "- Action this issue with a pull request adding a template "
                    f"file to {templates_link}.\n"
                    "- Close this issue if the file is not a good candidate "
                    "for templating."
                )
                create_issue(issue_title, issue_body)
            else:
                continue


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="TemplatingScripting",
        description="Commands for administrating templating of files across SciTools repos."
    )
    subparsers = parser.add_subparsers(required=True)

    notify = subparsers.add_parser(
        "notify-updates",
        description="Create issues on repos that use templates that have been updated.",
        epilog="This command is intended for running on the .github repo."
    )
    notify.set_defaults(func=notify_updates)

    prompt = subparsers.add_parser(
        "prompt-share",
        description="Make a PR author aware that they are modifying a templated file.",
        epilog="This command is intended for running on a PR on a 'target repo'."
    )
    prompt.add_argument(
        "pr_number",
        type=int,
        help="The number of the PR with content that might deserve templating."
    )
    prompt.set_defaults(func=prompt_share)

    # TODO: command to check templates/ dir aligns with _templating_config.json.
    #  Run this on PRs for the .github repo.

    parsed = parser.parse_args()
    parsed.func(parsed)


if __name__ == "__main__":
    main()
