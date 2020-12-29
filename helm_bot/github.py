import time
import logging
from subprocess import check_call
from .helper_functions import (
    delete_request,
    get_request,
    post_request,
    run_cmd,
)

logger = logging.getLogger()


def add_commit_push(
    filename: str,
    charts_to_update: list,
    chart_info: dict,
    repo_name: str,
    target_branch: str,
    token: str,
) -> None:
    """Perform add, commit, push commands on an edited file

    Args:
        filename (str): The file that has been edited
        charts_to_update (list): A list of charts the need to be updated
        chart_info (dict): A list of chart dependencies and their up-to-date versions
        repo_name (str): The name of the repository to push the changes to
        target_branch (str): The name of the branch to push the changes to
        token (str): A GitHub API token
    """
    # Add the edited file
    logger.info("Adding file: %s" % filename)

    add_cmd = ["git", "add", filename]
    result = run_cmd(add_cmd)

    if result["returncode"] != 0:
        logger.error(result["err_msg"])
        raise RuntimeError(result["err_msg"])

    logger.info("Successfully added file: %s" % filename)

    # Commit the edited file
    commit_msg = f"Bump chart dependencies {[chart for chart in charts_to_update]} to versions {[chart_info[chart] for chart in charts_to_update]}, respectively"
    logger.info("Committing file: %s" % filename)

    commit_cmd = ["git", "commit", "-m", commit_msg]
    result = run_cmd(commit_cmd)

    if result["returncode"] != 0:
        logger.error(result["err_msg"])
        raise RuntimeError(result["err_msg"])

    logger.info("Successfully committed file: %s" % filename)

    # Push changes to branch
    logger.info("Pushing commits to branch: %s" % target_branch)

    push_cmd = [
        "git",
        "push",
        f"https://HelmUpgradeBot:{token}@github.com/HelmUpgradeBot/{repo_name}",
        target_branch,
    ]
    result = run_cmd(push_cmd)

    if result["returncode"] != 0:
        logger.error(result["err_msg"])
        raise RuntimeError(result["err_msg"])

    logging.info("Successfully pushed changes to branch: %s" % target_branch)


def add_labels(labels: list, pr_url: str, token: str) -> None:
    """Adds labels to a Pull Request on GitHub

    Args:
        labels (list): A list of labels to add to the Pull Request
        pr_url (str): The URL of the open Pull Request
        token (str): A GitHub API token
    """
    logger.info("Adding labels to Pull Request: %s" % pr_url)
    logger.info("Adding labels: %s" % labels)

    post_request(
        pr_url,
        headers={"Authorization": f"token {token}"},
        json={"labels": labels},
    )


def check_fork_exists(repo_name: str, token: str) -> bool:
    """Check if HelmUpgradeBot has a fork of a GitHub repository

    Args:
        repo_name (str): The name of the repository to check for
        token (str): A GitHub API token

    Returns:
        bool: True if a fork exists, False if not
    """
    header = {"Authorization": f"token {token}"}
    resp = get_request(
        "https://api.github.com/users/HelmUpgradeBot/repos",
        headers=header,
        json=True,
    )

    fork_exists = bool([x for x in resp if x["name"] == repo_name])

    return fork_exists


def delete_old_branch(repo_name: str, target_branch: str, token: str) -> None:
    """Delete a branch of a GitHub repository

    Args:
        repo_name (str): The name of the repository
        target_branch (str): The name of the branch to be deleted
        token (str): A GitHub API token
    """
    header = {"Authorization": f"token {token}"}
    resp = get_request(
        f"https://api.github.com/repos/HelmUpgradeBot/{repo_name}/branches",
        headers=header,
        json=True,
    )

    if target_branch in [x["name"] for x in resp]:
        logger.info("Deleting branch: %s" % target_branch)
        delete_cmd = ["git", "push", "--delete", "origin", target_branch]
        result = run_cmd(delete_cmd)

        if result["returncode"] != 0:
            logger.error(result["err_msg"])
            raise RuntimeError(result["err_msg"])

        logger.info("Successfully deleted remote branch")

        delete_cmd = ["git", "branch", "-d", target_branch]
        result = run_cmd(delete_cmd)

        if result["returncode"] != 0:
            logger.error(result["err_msg"])
            raise RuntimeError(result["err_msg"])

        logger.info("Successfully deleted local branch")

    else:
        logger.info("Branch does not exist: %s" % target_branch)


def checkout_branch(
    repo_owner: str,
    repo_name: str,
    target_branch: str,
    token: str,
    pr_exists: bool,
) -> None:
    """Checkout a branch of a GitHub repository

    Args:
        repo_owner (str): The owner of the repository (user or org)
        repo_name (str): The name of the repository
        target_branch (str): The branch to checkout
        token (str): A GitHub API token
        pr_exists (bool): True if HelmUpgradeBot has a previously opened Pull
                          Request. Otherwise False.
    """
    fork_exists = check_fork_exists(repo_name, token)

    if fork_exists and not pr_exists:
        delete_old_branch(repo_name, target_branch, token)

        logger.info("Pulling main branch of: %s/%s" % (repo_owner, repo_name))
        pull_cmd = [
            "git",
            "pull",
            f"https://github.com/{repo_owner}/{repo_name}.git",
            "main",
        ]
        result = run_cmd(pull_cmd)

        if result["returncode"] != 0:
            logger.error(result["err_msg"])
            raise RuntimeError(result["err_msg"])

        logger.info("Successfully pulled main branch")

    logging.info("Checking out branch: %s" % target_branch)

    if pr_exists:
        chkt_cmd = ["git", "checkout", target_branch]
    else:
        chkt_cmd = ["git", "checkout", "-b", target_branch]

    result = run_cmd(chkt_cmd)

    if result["returncode"] != 0:
        logger.error(result["err_msg"])
        raise RuntimeError(result["err_msg"])

    logger.info("Successfully checked out branch")


def clone_fork(repo_name: str) -> None:
    """Clone a fork of a GitHub repository

    Args:
        repo_name (str): The repository to clone
    """
    logger.info("Cloning fork: %s" % repo_name)

    clone_cmd = [
        "git",
        "clone",
        f"https://github.com/HelmUpgradeBot/{repo_name}.git",
    ]
    result = run_cmd(clone_cmd)

    if result["returncode"] != 0:
        logger.error(result["err_msg"])
        raise RuntimeError(result["err_msg"])

    logger.info("Successfully cloned fork")


def create_pr(
    repo_api: str,
    base_branch: str,
    target_branch: str,
    token: str,
    labels: str = None,
) -> None:
    """Create a Pull Request to the original repository

    Args:
        repo_api (str): The API URL of the host repository
        base_branch (str): The name of the base branch for the PR
        target_branch (str): The name of the target branch for the PR
        token (str): A GitHub API token
        labels (str, optional): A list of labels to add to the PR.
                                Defaults to None.
    """
    logger.info("Creating Pull Request")

    pr = {
        "title": "Logging Helm Chart version upgrade",
        "body": "This PR is updating the local Helm Chart to the most recent Chart dependency versions.",
        "base": base_branch,
        "head": f"HelmUpgradeBot:{target_branch}",
    }

    resp = post_request(
        repo_api + "pulls",
        headers={"Authorization": f"token {token}"},
        json=pr,
        return_json=True,
    )

    logger.info("Pull Request created")

    if labels is not None:
        add_labels(labels, resp["issue_url"], token)


def find_existing_pr(repo_api: str, target_branch: str, token: str):
    """Check if the bot has an already open Pull Request

    Args:
        repo_api (str): The GitHub API URL to send queries to
        target_branch (str): The name of the PR source branch to search for
        token (str): A GitHub PAT to authorise queries with

    Returns:
        bool: True if HelmUpgradeBot already has an open PR. False otherwise.
    """
    logger.info("Finding Pull Requests opened by HelmUpgradeBot")

    header = {"Authorization": f"token {token}"}
    params = {"state": "open", "head": f"HelmUpgradeBot:{target_branch}"}

    resp = get_request(
        repo_api + "pulls", headers=header, params=params, json=True
    )

    if len(resp) >= 1:
        logger.info(
            "At least one Pull Request by HelmUpgradeBot open. "
            "Will push new commits to that PR."
        )
        return True
    else:
        logger.info(
            "No Pull Requests by HelmUpgradeBot found. "
            "A new PR will be opened."
        )
        return False


def make_fork(repo_name: str, repo_api: str, token: str) -> bool:
    """Create a fork of a GitHub repository

    Args:
        repo_name (str): The name of the repository
        repo_api (str): The API URL of the original repository
        token (str): A GitHub API token
    """
    logger.info("Forking repo: %s" % repo_name)

    post_request(
        repo_api + "forks", headers={"Authorization": f"token {token}"}
    )

    logger.info("Created fork")

    return True


def remove_fork(repo_name: str, token: str) -> bool:
    """Delete a fork of a GitHub repository

    Args:
        repo_name (str): The name of the repository
        token (str): A GitHub API token

    Returns:
        bool: False since fork no longer exists
    """
    fork_exists = check_fork_exists(repo_name, token)

    if fork_exists:
        logger.info("HelmUpgradeBot has a fork of: %s" % repo_name)

        delete_request(
            f"https://api.github.com/repos/HelmUpgradeBot/{repo_name}",
            headers={"Authorization": f"token {token}"},
        )

        time.sleep(5)
        logger.info("Deleted fork")

    else:
        logger.info("HelmUpgradeBot does not have a fork of: %s" % repo_name)

    return False


def set_git_config() -> None:
    """Setup git config"""
    logger.info("Setting up GitHub configuration for HelmUpgradeBot")

    check_call(["git", "config", "--global", "user.name", "HelmUpgradeBot"])
    check_call(
        [
            "git",
            "config",
            "--global",
            "user.email",
            "helmupgradebot.github@gmail.com",
        ]
    )
