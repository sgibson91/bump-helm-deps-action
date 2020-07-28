import logging

from .helper_functions import get_request, post_request, run_cmd

logger = logging.getLogger()


def add_commit_push(
    filename: str,
    charts_to_update: list,
    chart_info: dict,
    repo_name: str,
    target_branch: str,
    token: str,
) -> None:
    # Add the edited file
    logger.info("Adding file: %s" % filename)

    add_cmd = ["git", "add", filename]
    result = run_cmd(add_cmd)

    if result["returncode"] != 0:
        logger.error(result["err_msg"])
        # Add clean up functions here
        raise RuntimeError(result["err_msg"])

    logger.info("Successfully added file: %s" % filename)

    # Commit the edited file
    commit_msg = f"Bump chart dependencies {[chart for chart in charts_to_update]} to versions {[chart_info[chart]['version'] for chart in charts_to_update]}, respectively"
    logger.info("Committing file: %s" % filename)

    commit_cmd = ["git", "commit", "-m", commit_msg]
    result = run_cmd(commit_cmd)

    if result["returncode"] != 0:
        logger.error(result["err_msg"])
        # Add clean_up functions here
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
        # Add clean-up functions here
        raise RuntimeError(result["err_msg"])

    logging.info("Successfully pushed changes to branch: %s" % target_branch)


def add_labels(labels: list, pr_url: str, token: str) -> None:
    logger.info("Adding labels to Pull Request: %s" % pr_url)
    logger.info("Adding labels: %s" % labels)

    post_request(
        pr_url,
        headers={"Authorization": f"token {token}"},
        json={"labels": labels},
    )


def check_fork_exists(repo_name: str) -> bool:
    resp = get_request("https://api.github.com/users/HelmUpgradeBot/repos")

    fork_exists = bool([x for x in resp.json() if x["name"] == repo_name])

    return fork_exists


def checkout_branch(
    repo_owner: str, repo_name: str, target_branch: str
) -> None:
    fork_exists = check_fork_exists(repo_name)

    if fork_exists:
        # delete_old_branch()

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
            # Add clean-up functions here
            raise RuntimeError(result["err_msg"])

        logger.info("Successfully pulled main branch")

    logging.info("Checking out branch: %s" % target_branch)
    chkt_cmd = ["git", "checkout", "-b", target_branch]
    result = run_cmd(chkt_cmd)

    if result["returncode"] != 0:
        logger.error(result["err_msg"])
        # Add clean-up functions here
        raise RuntimeError(result["err_msg"])

    logger.info("Successfully checked out branch")


def clone_fork(repo_name: str) -> None:
    logger.info("Cloning fork: %s" % repo_name)

    clone_cmd = [
        "git",
        "clone",
        f"https://github.com/HelmUpgradeBot/{repo_name}.git",
    ]
    result = run_cmd(clone_cmd)

    if result["returncode"] != 0:
        logger.error(result["err_msg"])
        # Add clean-up functions here
        raise RuntimeError(result["err_msg"])

    logger.info("Successfully cloned fork")
