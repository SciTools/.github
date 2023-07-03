"""
This module visualises SciTools issues and PR's in a dashboard, to assist the
dev team in keeping the repos healthy.
"""

import json
from pathlib import Path
from subprocess import run
from typing import List


csv_path = Path(__file__).parent / "peloton.csv"


def _get_peloton_logins() -> List[str]:
    query = """
        query { 
          organization(login: "SciTools") { 
            team(slug: "Peloton") {
              members(first: 100) {
                nodes {
                  login
                }
              }
            }
          }
        }
    """
    # Useful for reading GHA logs.
    print(query)
    output = run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True,
        text=True,
        check=True
    )

    data = json.loads(output.stdout)["data"]
    nodes = data["organization"]["team"]["members"]["nodes"]
    logins = [node["login"] for node in nodes]
    logins.extend([
        # @rcomer has asked not to receive notifications for the
        #  SciTools/peloton GitHub team, so is not a member and instead is
        #  added here.
        "rcomer",
        "codecov[bot]",
        "github-actions[bot]",
        "pre-commit-ci[bot]",
        "scitools-ci[bot]"
    ])

    return logins


peloton_logins = _get_peloton_logins()

# TODO: expand list if this idea gets traction. Possibly blanket all SciTools?
peloton_repos = [
    "SciTools/cf-units",
    "SciTools/iris",
    "SciTools/iris-grib",
    "SciTools/nc-time-axis",
    "SciTools/python-stratify",
    "SciTools/tephi",
    "SciTools-incubator/iris-esmf-regrid",
]
