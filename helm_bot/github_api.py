import jmespath
from loguru import logger
from requests import put

from .http_requests import get_request, patch_request, post_request


def add_labels(labels, pr_url, header):
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


def assign_reviewers(reviewers, team_reviewers, pr_url, header):
    """Request reviews from GitHub users on a Pull Request

    Args:
        reviewers (list): A list of GitHub user to request reviews from
            (**excluding** the leading `@` symbol)
        team_reviewers (list): A list of GitHub Teams to request a review from. In the
            form <ORG_NAME>/<TEAM_NAME>.
        pr_url (str): The API URL of the Pull Request (pulls endpoint) to send
            the request to
        header (dict): A dictionary of headers to send with the request. Must
            contain an authorisation token.
    """
    logger.info("Assigning reviewers to Pull Request: {}", pr_url)
    json = {}

    if reviewers:
        logger.info("Assigning reviewers: {}", reviewers)
        json["reviewers"] = reviewers
    if team_reviewers:
        logger.info("Assigning team reviewers: {}", team_reviewers)
        json["team_reviewers"] = team_reviewers

    url = "/".join([pr_url, "requested_reviewers"])
    post_request(
        url,
        headers=header,
        json=json,
    )


def create_commit(
    api_url,
    header,
    path,
    branch,
    sha,
    commit_msg,
    content,
):
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


def create_ref(api_url, header, ref, sha):
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


def create_update_pr(
    api_url,
    header,
    base_branch,
    head_branch,
    chart_name,
    chart_info,
    charts_to_update,
    labels,
    reviewers,
    team_reviewers,
    pr_exists,
    pr_number=None,
):
    """Create or update a Pull Request via the GitHub API

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
        team_reviewers (list): A list of GitHub Teams to request a review from. In the
            form <ORG_NAME>/<TEAM_NAME>.
        pr_exists (bool): True if a Pull Request exists.
        pr_number (int): The number of an existing Pull Request to update. None otherwise.
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
    }

    if pr_exists:
        url = "/".join([url, str(pr_number)])
        pr["state"] = "open"

        resp = patch_request(
            url,
            headers=header,
            json=pr,
            return_json=True,
        )

        logger.info(f"Pull Request #{resp['number']} updated!")
    else:
        pr["head"] = head_branch

        resp = post_request(
            url,
            headers=header,
            json=pr,
            return_json=True,
        )

        logger.info(f"Pull Request #{resp['number']} created!")

        if labels:
            add_labels(labels, resp["issue_url"], header)

        if reviewers or team_reviewers:
            assign_reviewers(reviewers, team_reviewers, resp["url"], header)


def find_existing_pr(api_url, header):
    """Check if the action already has an open Pull Request

    Args:
        api_url (str): The API URL of the GitHub repository to send requests to
        header (dict): A dictionary of headers to send with the GET request

    Returns:
        pr_exists (bool): True if there is already an open Pull Request.
            False otherwise.
        head_branch (str): The name of the branch to send commits to. None if a Pull
            Request does not already exist.
        number (int): The number of the existing Pull Request. None otherwise.
    """
    logger.info(
        "Finding Pull Requests previously opened to bump helm chart dependencies"
    )

    url = "/".join([api_url, "pulls"])
    params = {"state": "open", "sort": "created", "direction": "desc"}
    resp = get_request(url, headers=header, params=params, output="json")

    # Expression to match the head ref
    matches = jmespath.search("[*].head.label", resp)
    indx, match = next(
        (
            (indx, match)
            for (indx, match) in enumerate(matches)
            if "helm_dep_bump" in match
        ),
        (None, None),
    )

    if (indx is None) and (match is None):
        logger.info(
            "No relevant Pull Requests found. A new Pull Request will be opened."
        )
        return False, None, None
    else:
        logger.info(
            "Relevant Pull Request found. Will push new commits to this Pull Request."
        )

        ref = match.split(":")[-1]
        number = resp[indx]["number"]

        return True, ref, number


def get_contents(api_url, header, path, ref):
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


def get_ref(api_url, header, ref):
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
