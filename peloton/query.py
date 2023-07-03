"""
Query the GitHub API for issue and PR data to inform managing SciTools.
"""

import datetime
from itertools import chain
from os import environ
import re

from github import Github
import pandas as pd

from common import csv_path, peloton_repos


issue_keys_keep = [
    "node_id",
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

    github_token = environ.get("GH_TOKEN") or environ.get("GITHUB_TOKEN")
    if github_token is None:
        message = "Please set the GH_TOKEN or GITHUB_TOKEN environment variable."
        raise EnvironmentError(message)
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

    open_df = issues_df[issues_df["state"] == "open"]
    assigned_df = open_df[open_df["assignee_logins"] != ""]
    assignee_counts = (assigned_df["assignee_logins"].value_counts())
    assignee_counts_str = pd.Series(
        [
            f"{count:0>3d} - {assignee}"
            for assignee, count
            in assignee_counts.items()
        ],
        index=assignee_counts.index,
        name="assignee_count",
    )
    issues_df = issues_df.join(assignee_counts_str, on="assignee_logins")

    issues_df.to_csv(csv_path)
