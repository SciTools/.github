"""
This module visualises SciTools issues and PR's in a dashboard, to assist the
dev team in keeping the repos healthy.
"""

from pathlib import Path


csv_path = Path(__file__).parent / "peloton.csv"

# TODO: use the SciTools/peloton user group instead.
peloton_logins = [
    "bjlittle",
    "bsherratt",
    "ESadek-MO",
    "codecov[bot]",
    "HGWright",
    "jamesp",
    "lbdreyer",
    "pp-mo",
    "rcomer",
    "stephenworsley",
    "tkknight",
    "trexfeathers",
    "wjbenfold",
    "dependabot[bot]",
    "github-actions[bot]",
    "pre-commit-ci[bot]",
    "scitools-ci[bot]",
]

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
