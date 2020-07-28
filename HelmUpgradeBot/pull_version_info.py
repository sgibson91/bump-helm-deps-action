import yaml

from .helper_functions import get_request


def pull_version_from_requirements_file(
    output_dict: dict, dependency: str, filename: str
) -> dict:  # noqa: E501
    """Pull dependency versions requirements.yml file.

    Args:
        output_dict (dict): The dictionary to store versions in
        dependency (str): The dependency to get a new version for
        url (str): The URL of the remotely hosted versions
    """
    with open(filename, "r") as stream:
        chart_reqs = yaml.safe_load(stream)

    output_dict[dependency] = chart_reqs[dependency]["version"]

    return output_dict


def pull_version_from_chart_file(
    output_dict: dict, dependency: str, url: str
) -> dict:  # noqa: E501
    """Pull recent, up-to-date version from remote host stored in a Chart.yml
    file.

    Args:
        output_dict (dict): The dictionary to store versions in
        dependency (str): The dependency to get a new version for
        url (str): The URL of the remotely hosted versions
    """
    chart_reqs = yaml.safe_load(get_request(url, text=True))
    output_dict[dependency] = chart_reqs["version"]

    return output_dict


def pull_version_from_github_pages(
    output_dict: dict, dependency: str, url: str
) -> dict:
    """Pull recent, up-to-date version from remote host listed on a GitHub Pages
    site.

    Args:
        output_dict (dict): The dictionary to store versions in
        dependency (str): The dependency to get a version for
        url (str): The URL of the remotely hosted versions
    """
    chart_reqs = yaml.safe_load(get_request(url, text=True))
    updates_sorted = sorted(
        chart_reqs["entries"][dependency], key=lambda k: k["created"]
    )
    output_dict[dependency] = updates_sorted[-1]["version"]

    return output_dict
