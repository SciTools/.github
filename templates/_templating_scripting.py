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

# A mechanism for disabling the issues and comments if the dev team is
#  deliberately doing intense work on templates and templated files (the volume
#  of un-actioned notifications would be overwhelming).
SPRING_CLEANING = True

SCITOOLS_URL = "https://github.com/SciTools"
TEMPLATES_DIR = Path(__file__).parent.resolve()
TEMPLATE_REPO_ROOT = TEMPLATES_DIR.parent
# ensure any new bots have both a "app/" prefix and a "[bot]" postfix version
BOTS = ["dependabot[bot]", "app/dependabot", "pre-commit-ci[bot]", "app/pre-commit-ci"]


def git_command(command: str) -> str:
    command = shlex.split(f"git {command}")
    return check_output(command).decode("utf-8").strip()


class Config:
    """Convenience to give the config JSON some readable structure."""
    class TargetRepo(NamedTuple):
        repo: str
        path_in_repo: Path

    def __init__(self):
        with (TEMPLATES_DIR / "_templating_include.json").open() as file_read:
            config = json.load(file_read)

        self.templates: dict[Path, list[Config.TargetRepo]] = {}

        for _template, _target_repos in config.items():
            template = TEMPLATES_DIR / _template
            assert template.is_file(), f"{template} does not exist."
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

    if SPRING_CLEANING:
        print(
            "Spring cleaning is in effect; no issues/comments will be posted."
        )
        return

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
                f"The template for `{path_in_repo}` has been updated; see the "
                "diff below. Please either:\n\n"
                
                "- Action this issue with a pull request applying some/all of "
                f"these changes to `{path_in_repo}`.\n"
                "- Close this issue if _none_ of these changes are appropriate "
                "for this repo.\n\n"
                "Also consider reviewing a full diff between the template and "
                f"`{path_in_repo}`, in case other valuable shared conventions "
                f"have previously been missed.\n\n"

                "## File Links\n\n"
                f"- The file in this repo: {file_link}\n"
                f"- The template file in the **.github** repo: {template_link}\n\n"
                # TODO: a link to the whole diff compared to the template?

                "## Diff\n\n"
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
    if SPRING_CLEANING:
        print(
            "Spring cleaning is in effect; no issues/comments will be posted."
        )
        return

    def gh_json(sub_command: str, field: str) -> dict:
        command = shlex.split(f"gh {sub_command} --json {field}")
        return json.loads(check_output(command))

    pr_number = args.pr_number
    # Can use a URL here for local debugging:
    # pr_number = "https://github.com/SciTools/iris/pull/6496"

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

    with (TEMPLATES_DIR / "_templating_exclude.json").open() as file_read:
        ignore_dict = json.load(file_read)

    def get_commit_authors(commit_json: dict) -> list[str]:
        return [a["login"] for a in commit_json["authors"]]

    def get_all_authors() -> set[str]:
        """Get all the authors of all the commits in the PR."""
        commits = gh_json(f"pr view {pr_number}", "commits")["commits"]

        return set(
            commit_author
            for commit in commits
            for commit_author in get_commit_authors(commit)
        )

    human_authors = get_all_authors() - set(BOTS)
    if human_authors == set():
        review_body = (
            f"### [Templating]({SCITOOLS_URL}/.github/blob/main/templates)\n\n"
            "Version numbers are not typically covered by templating. It is "
            "expected that this PR is 100% about advancing version numbers, "
            "which would not require any templating follow-up. **Please double-"
            "check for any other changes that might be suitable for "
            "templating**."
        )
        with NamedTemporaryFile("w") as file_write:
            file_write.write(review_body)
            file_write.flush()
            gh_command = shlex.split(
                f"gh pr review {pr_number} --comment --body-file {file_write.name}"
            )
            run(gh_command, check=True)
        return

    def create_issue(title: str, body: str) -> None:
        assignee = author

        # Check that an issue with this title isn't already on the .github repo.
        existing_issues = gh_json(
            "issue list --state all --repo SciTools/.github", "title"
        )
        if any(issue["title"] == title for issue in existing_issues):
            return

        if assignee in BOTS:
            # if the author is a bot, we don't want to assign the issue to the bot
            # so instead choose a human author from the latest commit
            assignee = list(human_authors)[0]

        with NamedTemporaryFile("w") as file_write:
            file_write.write(body)
            file_write.flush()
            gh_command = shlex.split(
                "gh issue create "
                f'--title "{title}" '
                f"--body-file {file_write.name} "
                "--repo SciTools/.github "
                f"--assignee {assignee}"
            )
            issue_url = check_output(gh_command).decode("utf-8").strip()
        short_ref = url_to_short_ref(issue_url)
        # GitHub renders the full text of a cross-ref when it is in a list.
        review_body = f"- [ ] Please see: {short_ref}"
        gh_command = shlex.split(
            f'gh pr review {pr_number} --request-changes --body "{review_body}"'
        )
        run(gh_command, check=True)

    issue_title = f"Share {pr_short_ref} changes via templating?"

    templates_relative = TEMPLATES_DIR.relative_to(TEMPLATE_REPO_ROOT)
    templates_url = f"{SCITOOLS_URL}/.github/tree/main/{templates_relative}"
    body_intro = (
        f"## [Templating]({SCITOOLS_URL}/.github/blob/main/templates/README.md)\n\n"
        f"{pr_short_ref} (by @{author}) includes changes that may be worth "
        "sharing via templating. For each file listed below, please "
        "either:\n\n"
        "- Action the suggestion via a pull request editing/adding the "
        f"relevant file in the [templates directory]({templates_url}).\n"
        "- Dismiss the suggestion if the changes are not suitable for "
        "templating."
    )

    templated_list = []
    body_templated = (
        "\n### Templated files\n\n"
        "The following changed files are templated:\n"
    )

    candidates_list = []
    body_candidates = (
        "\n### Template candidates\n\n"
        "The following changed files are not currently templated, but their "
        "parent directories suggest they may be good candidates for "
        "a new template to be created:\n"
    )

    for changed_path in changed_paths:
        template = CONFIG.find_template(pr_repo, changed_path)
        is_templated = template is not None
        ignored = changed_path in ignore_dict[pr_repo]
        if ignored:
            continue
        if is_templated:
            template_relative = template.relative_to(TEMPLATE_REPO_ROOT)
            template_url = (
                f"{SCITOOLS_URL}/.github/blob/main/{template_relative}"
            )
            template_link = f"[`{template_relative}`]({template_url})"

            templated_list.append(
                f"- [ ] `{changed_path}`, templated by {template_link}"
            )

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
                candidates_list.append(f"- [ ] `{changed_path}`")

    if templated_list or candidates_list:
        body_args = [body_intro]
        if templated_list:
            body_args.append(body_templated)
            body_args.extend(templated_list)
        if candidates_list:
            body_args.append(body_candidates)
            body_args.extend(candidates_list)

        issue_body = "\n".join(body_args)
        create_issue(issue_title, issue_body)


def check_dir(args: argparse.Namespace) -> None:
    """Ensures templates/ dir aligns with _templating_include.json.

    This function is intended for running on the .github repo.
    """

    # Always passed (by common code), but never used in this routine.
    _ = args

    templates = [Path(TEMPLATES_DIR, template_name) for template_name in TEMPLATES_DIR.rglob("*")]
    for template in templates:
        if template.is_file():
            assert template in CONFIG.templates, f"{template} is not in _templating_include.json"


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

    check = subparsers.add_parser(
        "check_dir",
        description="Check templates/ dir aligns with _templating_include.json.",
        epilog="This command is intended for running on the .github repo."
    )
    check.set_defaults(func=check_dir)

    parsed = parser.parse_args()
    parsed.func(parsed)


if __name__ == "__main__":
    main()
