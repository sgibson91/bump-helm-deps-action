import os
import yaml
import shutil
import logging

from itertools import compress

from .helper_functions import run_cmd

from .github import (
    add_commit_push,
    check_fork_exists,
    checkout_branch,
    clone_fork,
    create_pr,
    make_fork,
)

HERE = os.getcwd()

logger = logging.getLogger()


def check_versions(
    chart_name: str, chart_info: dict, dry_run: bool = False
) -> list:
    """Check if chart dependencies are up-to-date

    Args:
        chart_name (str): The chart to check the dependencies of
        chart_info (dict): Dictionary containing chart version info
        dry_run (bool, optional): For a dry-run, don't edit files.
                                  Defaults to False.

    Returns:
        list: A list of chart dependencies that need updating
    """
    charts = list(chart_info.keys())
    charts.remove(chart_name)

    condition = [
        (
            chart_info[chart]["version"]
            != chart_info[chart_name][chart]["version"]
        )
        for chart in charts
    ]
    charts_to_update = list(compress(charts, condition))

    if condition.any() and (not dry_run):
        logger.info(
            "Helm upgrade required for the following charts: %s"
            % charts_to_update
        )
    elif condition.any() and dry_run:
        logger.info(
            "Helm upgrade required for the following charts: %s. PR won't be opened due to --dry-run flag being set."
            % charts_to_update
        )
    else:
        logger.info(
            "%s is up-to-date with all current chart dependency releases!"
            % chart_name
        )

    return charts_to_update


def clean_up(repo_name: str) -> None:
    """Clean up the locally cloned repository

    Args:
        repo_name (str): The repository name
    """
    cwd = os.getcwd()
    this_dir = cwd.split("/")[-1]
    if this_dir == repo_name:
        os.chdir(os.pardir)

    if os.path.exists(repo_name):
        logger.info("Deleting local repository: %s" % repo_name)
        shutil.rmtree(repo_name)
        logger.info("Deleted local repository: %s" % repo_name)


def get_chart_versions(
    chart_name: str, repo_owner: str, repo_name: str
) -> dict:
    """Get the versions of dependent charts

    Args:
        chart_name (str): The main chart to check
        repo_owner (str): The repository/chart owner
        repo_name (str): The name of the repository hosting the chart

    Returns:
        dict: A dictionary containing the chart dependencies and their
              up-to-date versions
    """
    chart_info = {}
    chart_urls = {
        chart_name: f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/main/{chart_name}/requirements.yaml",
        "binderhub": "https://raw.githubusercontent.com/jupyterhub/helm-chart/gh-pages/index.yaml",
        "nginx-ingress": "https://raw.githubusercontent.com/helm/charts/master/stable/nginx-ingress/Chart.yaml",
    }

    for (chart, chart_url) in chart_urls.items():
        if "requirements.yaml" in chart_url:
            # Get the versions from a requirements.yaml file
            pass
        elif "Chart.yaml" in chart_url:
            # Get the versions from a Chart.yaml file
            pass
        elif "/gh-pages/" in chart_url:
            # Get the versions from a gh-pages page
            pass
        else:
            msg = (
                "Scraping from the following URL type is currently not implemented\n\t%s"
                % chart_url
            )
            logger.error(NotImplementedError(msg))
            raise NotImplementedError(msg)

    return chart_info


def update_local_file(
    chart_name: str, charts_to_update: list, chart_info: dict
) -> None:
    """Update the local helm chart

    Args:
        chart_name (str): The name of the helm chart
        charts_to_update (list): A list of the dependencies that need updating
        chart_info (dict): A dictionary of the dependent charts and their
                           up-to-date versions
    """
    logger.info("Updating local helm chart: %s" % chart_name)

    filename = os.path.join(HERE, chart_name, "requirements.yaml")
    with open(filename, "r") as stream:
        chart_yaml = yaml.safe_load(stream)

    for chart in charts_to_update:
        for dep in chart_yaml["dependencies"]:
            if dep["name"] == chart:
                dep["version"] = chart_info[chart]["version"]

    with open(filename, "w") as stream:
        yaml.safe_dump(chart_yaml, stream)

    logger.info("Updated file: %s" % filename)


def upgrade_chart(
    chart_name: str,
    chart_info: dict,
    charts_to_update: list,
    repo_owner: str,
    repo_name: str,
    repo_api: str,
    base_branch: str,
    target_branch: str,
    token: str,
    labels: list,
) -> None:
    """Upgrade the dependencies in the helm chart

    Args:
        chart_name (str): The name of the helm-chart
        chart_info (dict): A dictionary of the dependencies and their versions
        charts_to_update (list): The dependencies that need updating
        repo_owner (str): The owner of the repository (user or org)
        repo_name (str): The name of the repository hosting the helm chart
        repo_api (str): The API URL of the original repository
                        (not HelmUpgradeBot's fork)
        base_branch (str): The base branch for opening the Pull Request
        target_branch (str): The target branch for opening the Pull Request
        token (str): A GitHub API token
        labels (list): A list of labels to add the the Pull Request
    """
    filename = os.path.join(HERE, chart_name, "requirements.yaml")

    fork_exists = check_fork_exists(repo_name)

    if fork_exists:
        make_fork(repo_name, repo_api, token)
    clone_fork(repo_name)

    os.chdir(repo_name)
    checkout_branch(repo_owner, repo_name, target_branch)
    update_local_file(chart_name, charts_to_update, chart_info)
    add_commit_push(
        filename, charts_to_update, chart_info, repo_name, target_branch, token
    )
    create_pr(repo_api, base_branch, target_branch, token, labels)
