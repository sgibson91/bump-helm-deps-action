import base64
import os
import random
import string
from itertools import compress, product

from loguru import logger
from ruamel.yaml import YAML

from .github_api import (
    create_commit,
    create_pr,
    create_ref,
    find_existing_pr,
    get_contents,
    get_ref,
)
from .http_requests import get_request
from .pull_version_info import get_chart_versions

HERE = os.getcwd()
yaml = YAML(typ="safe", pure=True)


def edit_config(
    download_url: str,
    header: dict,
    charts_to_update: list,
    chart_info: dict,
) -> str:
    """Update the helm chart dependencies

    Args:
        download_url (str): The URL where the chart config can be downloaded from
        header (dict): A dictionary of headers to with any requests. Must
            contain an authorisation token.
        charts_to_update (list): A list of helm chart dependencies that can be
            updated
        chart_info (dict): A dictionary of the dependent charts and their most
            recent versions

    Returns:
        str: The updated helm chart config
    """
    resp = get_request(download_url, headers=header, output="text")
    chart_yaml = yaml.load(resp)

    for chart, dep in product(charts_to_update, chart_yaml["dependencies"]):
        if dep["name"] == chart:
            dep["version"] = chart_info[chart]

    base64_bytes = base64.b64encode(str(chart_yaml).encode("utf-8"))
    chart_yaml = base64_bytes.decode("utf-8")

    return chart_yaml


def upgrade_chart_deps(
    api_url: str,
    header: dict,
    chart_path: str,
    base_branch: str,
    head_branch: str,
    charts_to_update: list,
    chart_info: dict,
    pr_exists: bool,
) -> None:
    """Upgrade the dependencies in the helm chart to the most recent version

    Args:
        api_url (str): The URL to send the request to
        header (dict): A dictionary of headers to send with the request. Must
            contain and authorisation token.
        chart_path (str): The path to the file that contains the chart's
            dependencies
        base_branch (str): The name of the branch to open the Pull Request
            against
        head_branch (str): The name of the branch to open the Pull Request from
        charts_to_update (list): A list of the helm chart dependencies that need
            updating
        chart_info (dict): A dictionary of the helm chartdependencies and their
            versions
        pr_exists (bool): If a Pull Request already exists, commit to it's head
            branch instead of opening a new one
    """
    if not pr_exists:
        # Get reference to HEAD of base_branch
        resp = get_ref(api_url, header, base_branch)

        # Create head_branch
        create_ref(api_url, header, head_branch, resp["object"]["sha"])

        # Get the file download URL and blob sha
        resp = get_contents(api_url, header, chart_path, base_branch)
    else:
        # Get the file download URL and blob sha
        resp = get_contents(api_url, header, chart_path, head_branch)

    chart_yaml_url = resp["download_url"]
    blob_sha = resp["sha"]

    chart_yaml = edit_config(chart_yaml_url, header, charts_to_update, chart_info)

    # Create a commit
    commit_msg = f"Bump charts {[chart for chart in charts_to_update]} to versions {[chart_info[chart] for chart in charts_to_update]}, respectively"
    create_commit(
        api_url, header, chart_path, head_branch, blob_sha, commit_msg, chart_yaml
    )


def compare_dependency_versions(chart_info: dict, chart_name: str) -> list:
    """Compare the currently deployed helm chart dependencies against the most
    recently available and ascertain if a dependency can be updated

    Args:
        chart_info (dict): A dictionary of the helm chartdependencies and their
            versions
        chart_name (str): The name of the local helm chart

    Returns:
        charts_to_update (list): A list of the helm chart dependencies that need
            updating
    """
    charts = list(chart_info.keys())
    charts.remove(chart_name)

    condition = [
        (chart_info[chart] != chart_info[chart_name][chart]) for chart in charts
    ]
    return list(compress(charts, condition))


def run(
    api_url: str,
    header: dict,
    chart_path: str,
    chart_urls: dict,
    base_branch: str,
    head_branch: str,
    labels: list = [],
    reviewers: list = [],
    dry_run: bool = False,
) -> None:
    """Run the action to check if the helm chart dependencies are up to date

    Args:
        api_url (str): The URL to send the request to
        header (dict): A dictionary of headers to send with the request. Must
            contain and authorisation token.
        chart_path (str): The path to the file that contains the chart's
            dependencies
        chart_urls (dict): A dictionary storing the location of the dependency
            charts and their versions
        base_branch (str): The name of the branch to open the Pull Request
            against
        head_branch (str): The name of the branch to open the Pull Request from
        labels (list, optional): A list of labels to apply to the Pull Request.
            Defaults to [].
        reviewers (list, optional): A list of GitHub users to request reviews
            from. Defaults to [].
        dry_run (bool, optional): Perform a dry-run and do not open a Pull
            Request. A list of the chart dependencies that can be updated will
            be printed to the console. Defaults to False.
    """
    chart_name = chart_path.split("/")[-2]

    # Check if Pull Request exists
    pr_exists, branch_name = find_existing_pr(api_url, header)

    # Get and compare the helm chart dependencies
    if branch_name is None:
        chart_info = get_chart_versions(
            api_url, header, chart_path, chart_urls, base_branch
        )
    else:
        chart_info = get_chart_versions(
            api_url, header, chart_path, chart_urls, branch_name
        )

    charts_to_update = compare_dependency_versions(chart_info, chart_name)

    if (len(charts_to_update) > 0) and (not dry_run):
        logger.info(
            "The following chart dependencies can be updated: {}", charts_to_update
        )

        if branch_name is None:
            random_id = "".join(random.sample(string.ascii_letters, 4))
            head_branch = "-".join([head_branch, random_id])
        else:
            head_branch = branch_name

        upgrade_chart_deps(
            api_url,
            header,
            chart_path,
            base_branch,
            head_branch,
            charts_to_update,
            chart_info,
            pr_exists,
        )

        if not pr_exists:
            create_pr(api_url, header, base_branch, head_branch, labels, reviewers)

    elif (len(charts_to_update) > 0) and dry_run:
        logger.info(
            "The following chart dependencies can be updated: {}. Pull Request will not be opened due to the --dry-run flag being set.",
            charts_to_update,
        )

    else:
        logger.info("All chart dependencies are up-to-date!")
