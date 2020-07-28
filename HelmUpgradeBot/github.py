import logging

from .helper_functions import post_request, run_cmd

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
