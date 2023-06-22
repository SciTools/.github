"""
Query the GitHub API for issue and PR data to inform managing SciTools.
"""

import datetime
from itertools import chain
from pathlib import Path
import re

from github import Github
import pandas as pd

from common import peloton_repos

CSV_PATH = Path(__file__).parent / "peloton.csv"

issue_keys_keep = [
    "html_url",
    "number",
    "title",
    "state",
    "comments",
    "created_at",
    "updated_at",
    "closed_at",
    "draft",
]


if __name__ == "__main__":
    since = datetime.datetime.now() - datetime.timedelta(weeks=6)

    # TODO: allow this to work with GHA OR a user's local token.
    token_path = Path().home() / ".api_keys" / "github-token.txt"
    github_token = token_path.read_text().strip()
    g = Github(github_token)

    issue_dicts = []
    for repo_name in peloton_repos:
        repo = g.get_repo(repo_name)
        discussion_label_id = 0
        feature_branch_label_id = 0
        labels = repo.get_labels()
        for label in labels:
            if re.search(r"decision|help|discussion", label.name, flags=re.IGNORECASE):
                discussion_label_id = label.raw_data["id"]
                break
        for label in labels:
            if re.search(r"feature branch", label.name, flags=re.IGNORECASE):
                feature_branch_label_id = label.raw_data["id"]
                break

        for issue in chain(
            repo.get_issues(state="open"), repo.get_issues(state="closed", since=since)
        ):
            issue_dict = issue.raw_data

            user_login = issue.user.login
            is_pr = issue.pull_request is not None
            assignee_logins = ", ".join([u.login for u in issue.assignees])

            if issue.state == "open":
                comments_count = issue_dict["comments"]
                if comments_count == 0:
                    final_comment_login = issue.user.login
                    final_comment_time = issue.created_at
                else:
                    final_comment = issue.get_comments()[comments_count - 1]
                    final_comment_login = final_comment.user.login
                    final_comment_time = final_comment.created_at

                votes = issue_dict["reactions"]["+1"]

                label_ids = [d["id"] for d in issue_dict["labels"]]
                discussion_wanted = discussion_label_id in label_ids
                feature_branch = feature_branch_label_id in label_ids

            else:
                # Don't need this info for closed issues.
                final_comment_login = None
                final_comment_time = None
                votes = 0
                discussion_wanted = False
                feature_branch = False

            if not is_pr:
                # Make keys consistent between PR and non-PR issues.
                issue_dict["draft"] = None
            issue_dict = {k: issue_dict[k] for k in issue_keys_keep}

            issue_dict["repo"] = repo.name
            issue_dict["repo_url"] = repo.html_url
            issue_dict["user_login"] = user_login
            issue_dict["is_pr"] = is_pr
            issue_dict["assignee_logins"] = assignee_logins
            issue_dict["final_comment_login"] = final_comment_login
            issue_dict["final_comment_time"] = final_comment_time
            issue_dict["votes"] = votes
            issue_dict["discussion_wanted"] = discussion_wanted
            issue_dict["feature_branch"] = feature_branch

            issue_dicts.append(issue_dict)

    issues_df = pd.DataFrame(issue_dicts)
    issues_df.to_csv(CSV_PATH)
