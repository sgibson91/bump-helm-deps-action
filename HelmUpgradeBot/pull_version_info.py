import yaml

from .helper_functions import get_request


def pull_version_from_requirements_file(
    output_dict: dict, chart_name: str, url: str, token: str
) -> dict:  # noqa: E501
    """Pull dependency versions requirements.yml file.

    Args:
        output_dict (dict): The dictionary to store versions in
        chart_name (str): The name of the helm chart
        url (str): The URL of the remotely hosted versions
        token (str): A GitHub API token
    """
    header = {"Authorization": f"token {token}"}
    chart_reqs = yaml.safe_load(get_request(url, headers=header, text=True))

    for chart in chart_reqs["dependencies"]:
        output_dict[chart_name][chart["name"]] = chart["version"]

    return output_dict


def pull_version_from_chart_file(
    output_dict: dict, dependency: str, url: str, token: str
) -> dict:  # noqa: E501
    """Pull recent, up-to-date version from remote host stored in a Chart.yml
    file.

    Args:
        output_dict (dict): The dictionary to store versions in
        dependency (str): The dependency to get a new version for
        url (str): The URL of the remotely hosted versions
        token (str): A GitHub API token
    """
    header = {"Authorization": f"token {token}"}
    chart_reqs = yaml.safe_load(get_request(url, headers=header, text=True))
    output_dict[dependency] = chart_reqs["version"]

    return output_dict


def pull_version_from_github_pages(
    output_dict: dict, dependency: str, url: str, token: str
) -> dict:
    """Pull recent, up-to-date version from remote host listed on a GitHub Pages
    site.

    Args:
        output_dict (dict): The dictionary to store versions in
        dependency (str): The dependency to get a version for
        url (str): The URL of the remotely hosted versions
        token (str): A GitHub API token
    """
    header = {"Authorization": f"token {token}"}
    chart_reqs = yaml.safe_load(get_request(url, headers=header, text=True))
    updates_sorted = sorted(
        chart_reqs["entries"][dependency], key=lambda k: k["created"]
    )
    output_dict[dependency] = updates_sorted[-1]["version"]

    return output_dict
