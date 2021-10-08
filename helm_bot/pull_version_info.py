import yaml

from .http_requests import get_request


def pull_from_requirements_file(
    api_url: str,
    header: dict,
    output_dict: dict,
    chart_name: str,
) -> dict:
    """Pull helm chart dependencies and versions from a requirements.yml/.yaml
    file.

    Args:
        api_url (str): The URL of the remotely hosted helm chart dependencies
        header (dict): [description]
        output_dict (dict): The dictionary to store chart versions in
        chart_name (str): The name of the helm chart to pull versions for

    Returns:
        output_dict (dict): A dictionary containing the names of the helm chart
            dependencies and their versions.
    """
    chart_reqs = yaml.safe_load(get_request(api_url, headers=header, output="text"))

    for chart in chart_reqs["dependencies"]:
        output_dict[chart_name][chart["name"]] = chart["version"]

    return output_dict


def pull_from_chart_file(
    api_url: str,
    header: dict,
    output_dict: dict,
    dependency: str,
) -> dict:
    """Pull helm chart dependencies and versions from a Chart.yml/.yaml file.

    Args:
        api_url (str): The URL of the remotely hosted helm chart dependencies
        header (dict): [description]
        output_dict (dict): The dictionary to store chart versions in
        dependency (str): The name of the helm chart dependency to pull
            versions for.

    Returns:
        output_dict (dict): A dictionary containing the names of the helm chart
            dependencies and their versions.
    """
    chart_reqs = yaml.safe_load(get_request(api_url, headers=header, output="text"))
    output_dict[dependency] = chart_reqs["version"]

    return output_dict


def pull_from_github_pages(
    api_url: str,
    header: dict,
    output_dict: dict,
    dependency: str,
) -> dict:
    """Pull helm chart dependencies and versions from remote host listed on a
    GitHub Pages site.

    Args:
        api_url (str): The URL of the remotely hosted helm chart dependencies
        header (dict): [description]
        output_dict (dict): The dictionary to store chart versions in
        dependency (str): The name of the helm chart dependency to pull
            versions for.

    Returns:
        output_dict (dict): A dictionary containing the names of the helm chart
            dependencies and their versions.
    """
    chart_reqs = yaml.safe_load(get_request(api_url, headers=header, output="text"))
    updates_sorted = sorted(
        chart_reqs["entries"][dependency], key=lambda k: k["created"]
    )
    output_dict[dependency] = updates_sorted[-1]["version"]

    return output_dict


def get_chart_versions(
    api_url: str,
    header: dict,
    chart_name: str,
    chart_urls: dict,
    branch_name: str,
) -> dict:
    """Get the versions of dependent helm charts

    Args:
        chart_name (str): The main helm chart to check
        repo_owner (str): The repository/chart owner
        repo_name (str): The name of the repository hosting the chart
        branch_name (str): The branch of `repo_name` to pull current chart
            versions from
        token (str): A GitHub API token
        pr_exists (bool): True if HelmUpgradeBot has previously opened a Pull
            Request. Default: False.

    Returns:
        dict: A dictionary containing the chart dependencies and their
              up-to-date versions
    """
    chart_info: dict = {}
    chart_info[chart_name] = {}

    for (chart, chart_url) in chart_urls.items():
        if ("requirements.yaml" in chart_url) or ("requirements.yml" in chart_url):
            chart_info = pull_from_requirements_file(
                chart_url,
                header,
                chart_info,
                chart,
            )
        elif ("Chart.yaml" in chart_url) or ("Chart.yml" in chart_url):
            chart_info = pull_from_chart_file(
                chart_url,
                header,
                chart_info,
                chart,
            )
        elif "/gh-pages/" in chart_url:
            chart_info = pull_from_github_pages(
                chart_url,
                header,
                chart_info,
                chart,
            )
        else:
            msg = (
                "Scraping from the following URL type is currently not implemented\n\t%s"
                % chart_url
            )
            raise NotImplementedError(msg)

    return chart_info
