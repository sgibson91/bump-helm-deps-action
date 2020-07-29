import pytest
import logging
from unittest.mock import patch, PropertyMock
from testfixtures import log_capture
from helm_bot.github import add_commit_push, add_labels, check_fork_exists


@log_capture()
def test_add_commit_push(capture):
    filename = "filename.txt"
    charts_to_update = ["chart-1", "chart-2"]
    chart_info = {"chart-1": "1.2.3", "chart-2": "4.5.6"}
    repo_name = "test_repo"
    target_branch = "test-branch"
    token = "this_is_a_token"

    logger = logging.getLogger()
    logger.info("Adding file: %s" % filename)
    logger.info("Successfully added file: %s" % filename)
    logger.info("Committing file: %s" % filename)
    logger.info("Successfully committed file: %s" % filename)
    logger.info("Pushing commits to branch: %s" % target_branch)
    logger.info("Successfully pushed changes to branch: %s" % target_branch)

    with patch(
        "helm_bot.github.run_cmd",
        return_value={"returncode": 0, "output": "", "err_msg": ""},
    ) as mock_run_cmd:
        add_commit_push(
            filename,
            charts_to_update,
            chart_info,
            repo_name,
            target_branch,
            token,
        )

        assert mock_run_cmd.call_count == 3

    capture.check_present()


@log_capture()
def test_add_commit_push_error(capture):
    filename = "filename.txt"
    charts_to_update = ["chart-1", "chart-2"]
    chart_info = {"chart-1": "1.2.3", "chart-2": "4.5.6"}
    repo_name = "test_repo"
    target_branch = "test-branch"
    token = "this_is_a_token"

    logger = logging.getLogger()
    logger.info("Adding file: %s" % filename)
    logger.error("Could not add file: %s" % filename)
    logger.info("Committing file: %s" % filename)
    logger.error("Could not commit file: %s" % filename)
    logger.info("Pushing commits to branch: %s" % target_branch)
    logger.error("Could not push to branch: %s" % target_branch)

    with pytest.raises(RuntimeError):
        add_commit_push(
            filename,
            charts_to_update,
            chart_info,
            repo_name,
            target_branch,
            token,
        )

    capture.check_present()


@log_capture()
def test_add_labels(capture):
    labels = ["label1", "label2"]
    pr_url = "http://jsonplaceholder.typicode.com/issues/1"
    token = "this_is_a_token"

    logger = logging.getLogger()
    logger.info("Add labels to Pull Request: %s" % pr_url)
    logger.info("Adding labels: %s" % labels)

    with patch("helm_bot.github.post_request") as mocked_func:
        add_labels(labels, pr_url, token)

        assert mocked_func.call_count == 1

    capture.check_present()


@patch(
    "helm_bot.github.get_request",
    return_value='[{"name": "test_repo1"}, {"name": "test_repo2"}]',
)
def test_check_fork_exists(mock_args):
    repo_name1 = "test_repo1"
    repo_name2 = "some_other_repo"
    token = "this_is_a_token"

    fork_exists1 = check_fork_exists(repo_name1, token)
    fork_exists2 = check_fork_exists(repo_name2, token)

    assert fork_exists1
    assert not fork_exists2

    assert mock_args.call_count == 2
    mock_args.assert_called_with(
        "https://api.github.com/users/HelmUpgradeBot/repos",
        headers={"Authorization": "token this_is_a_token"},
        text=True,
    )
