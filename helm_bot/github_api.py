from typing import Tuple, Union

import jmespath
from loguru import logger
from requests import put

from .http_requests import get_request, post_request


def add_labels(labels: list, pr_url: str, header: dict) -> None:
    """Assign labels to an open Pull Request. The labels must already exist in
    the repository.

    Args:
        labels (list): The list of labels to apply
        pr_url (str): The API URL of the Pull Request (issues endpoint) to
            send the request to
        header (dict): A dictionary of headers to send with the request. Must
            contain an authorisation token.
    """
    logger.info("Adding labels to Pull Request: {}", pr_url)
    logger.info("Adding labels: {}", labels)
    post_request(
        pr_url,
        headers=header,
        json={"labels": labels},
    )


def assign_reviewers(reviewers: list, pr_url: str, header: dict) -> None:
    """Request reviews from GitHub users on a Pull Request

    Args:
        reviewers (list): A list of GitHub user to request reviews from
            (**excluding** the leading `@` symbol)
        pr_url (str): The API URL of the Pull Request (pulls endpoint) to send
            the request to
        header (dict): A dictionary of headers to send with the request. Must
            contain an authorisation token.
    """
    logger.info("Assigning reviewers to Pull Request: {}", pr_url)
    logger.info("Assigning reviewers: {}", reviewers)
    url = "/".join([pr_url, "requested_reviewers"])
    post_request(
        url,
        headers=header,
        json={"reviewers": reviewers},
    )


def create_commit(
    api_url: str,
    header: dict,
    path: str,
    branch: str,
    sha: str,
    commit_msg: str,
    content: str,
) -> None:
    """Create a commit over the GitHub API by creating or updating a file

    Args:
        api_url (str): The URL to send the request to
        header (dict): A dictionary of headers to send with the request. Must
            include an authorisation token.
        path (str): The path to the file that is to be created or updated,
            relative to the repo root
        branch (str): The branch the commit should be made on
        sha (str): The SHA of the blob to be updated.
        commit_msg (str): A message describing the changes the commit applies
        content (str): The content of the file to be updated, encoded in base64
    """
    logger.info("Committing changes to file: {}", path)
    url = "/".join([api_url, "contents", path])
    body = {"message": commit_msg, "content": content, "sha": sha, "branch": branch}
    put(url, json=body, headers=header)


def create_ref(api_url: str, header: dict, ref: str, sha: str) -> None:
    """Create a new git reference (specifically, a branch) with GitHub's git
    database API endpoint

    Args:
        api_url (str): The URL to send the request to
        header (dict): A dictionary of headers to send with the request. Must
            include an authorisation token.
        ref (str): The reference or branch name to create
        sha (str): The SHA of the parent commit to point the new reference to
    """
    logger.info("Creating new branch: {}", ref)
    url = "/".join([api_url, "git", "refs"])
    body = {
        "ref": f"refs/heads/{ref}",
        "sha": sha,
    }
    post_request(url, headers=header, json=body)


def create_pr(
    api_url: str,
    header: dict,
    base_branch: str,
    head_branch: str,
    chart_name: str,
    chart_info: dict,
    charts_to_update: list,
    labels: list,
    reviewers: list,
) -> None:
    """Create a Pull Request via the GitHub API

    Args:
        api_url (str): The URL to send the request to
        header (dict): A dictionary of headers to send with the request. Must
            contain and authorisation token.
        base_branch (str): The name of the branch to open the Pull Request against
        head_branch (str): The name of the branch to open the Pull Request from
        chart_name (str): The name of the local helm chart
        chart_info (dict): A dictionary of the helm chartdependencies and their
            versions
        charts_to_update (list): A list of helm chart dependencies that can be
            updated
        labels (list): A list of labels to apply to the Pull Request
        reviewers (list): A list of GitHub users to request reviews from
    """
    logger.info("Creating Pull Request...")

    url = "/".join([api_url, "pulls"])
    pr = {
        "title": f"Bumping helm chart dependency versions: {chart_name}",
        "body": (
            f"This Pull Request is bumping the dependencies of the `{chart_name}` chart to the following versions.\n\n"
            + "\n".join(
                [
                    f"- {chart}: `{chart_info[chart_name][chart]}` -> `{chart_info[chart]}`"
                    for chart in charts_to_update
                ]
            )
        ),
        "base": base_branch,
        "head": head_branch,
    }
    resp = post_request(
        url,
        headers=header,
        json=pr,
        return_json=True,
    )

    logger.info("Pull Request created!")

    if len(labels) > 0:
        add_labels(labels, resp["issue_url"], header)

    if len(reviewers) > 0:
        assign_reviewers(reviewers, resp["url"], header)


def find_existing_pr(api_url: str, header: dict) -> Tuple[bool, Union[str, None]]:
    """Check if the action already has an open Pull Request

    Args:
        api_url (str): The API URL of the GitHub repository to send requests to
        header (dict): A dictionary of headers to send with the GET request

    Returns:
        pr_exists (bool): True if there is already an open Pull Request.
            False otherwise.
        head_branch (str): The name of the branch to send commits to
    """
    logger.info(
        "Finding Pull Requests previously opened to bump helm chart dependencies"
    )

    url = "/".join([api_url, "pulls"])
    params = {"state": "open", "sort": "created", "direction": "desc"}
    resp = get_request(url, headers=header, params=params, output="json")

    # Expression to match the head ref
    head_label_exp = jmespath.compile("[*].head.label")
    matching_labels = head_label_exp.search(resp)

    # Create list of labels of matching PRs
    matching_prs = [label for label in matching_labels if "helm_dep_bump" in label]

    if len(matching_prs) > 1:
        logger.info(
            "More than one Pull Request open. Will push new commits to the most recent Pull Request."
        )

        ref = matching_prs[0].split(":")[-1]

        return True, ref

    elif len(matching_prs) == 1:
        logger.info(
            "One Pull Request open. Will push new commits to this Pull Request."
        )

        ref = matching_prs[0].split(":")[-1]

        return True, ref

    else:
        logger.info(
            "No relevant Pull Requests found. A new Pull Request will be opened."
        )
        return False, None


def get_contents(api_url: str, header: dict, path: str, ref: str) -> dict:
    """Get the contents of a file in a GitHub repo over the API

    Args:
        api_url (str): The URL to send the request to
        header (dict): A dictionary of headers to send with the request. Must
            include an authorisation token.
        path (str): The path to the file that is to be created or updated,
            relative to the repo root
        ref (str): The reference (branch) the file is stored on

    Returns:
        dict: The JSON payload response of the request
    """
    logger.info("Downloading helm chart dependencies from url: {}", api_url)
    url = "/".join([api_url, "contents", path])
    query = {"ref": ref}
    return get_request(url, headers=header, params=query, output="json")


def get_ref(api_url: str, header: dict, ref: str) -> dict:
    """Get a git reference (specifically, a HEAD ref) using GitHub's git
    database API endpoint

    Args:
        api_url (str): The URL to send the request to
        header (dict): A dictionary of headers to send with the request. Must
            include an authorisation token.
        ref (str): The reference for which to return information for

    Returns:
        dict: The JSON payload response of the request
    """
    logger.info("Pulling info for ref: {}", ref)
    url = "/".join([api_url, "git", "ref", "heads", ref])
    return get_request(url, headers=header, output="json")
