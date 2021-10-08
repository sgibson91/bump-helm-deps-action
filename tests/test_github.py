import logging
from unittest.mock import call, patch

import pytest
import responses
from testfixtures import log_capture

from helm_bot.github import (
    add_commit_push,
    add_labels,
    assign_reviewers,
    check_fork_exists,
    checkout_branch,
    clone_fork,
    create_pr,
    delete_old_branch,
    make_fork,
    remove_fork,
    set_git_config,
)


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

    commit_msg = f"Bump chart dependencies {[chart for chart in charts_to_update]} to versions {[chart_info[chart] for chart in charts_to_update]}, respectively"
    expected_calls = [
        call(["git", "add", filename]),
        call(["git", "commit", "-m", commit_msg]),
        call(
            [
                "git",
                "push",
                f"https://HelmUpgradeBot:{token}@github.com/HelmUpgradeBot/{repo_name}",
                target_branch,
            ]
        ),
    ]

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
        assert mock_run_cmd.call_args_list == expected_calls

        capture.check_present()


@log_capture()
def test_add_commit_push_exception(capture):
    filename = "filename.txt"
    charts_to_update = ["chart-1", "chart-2"]
    chart_info = {"chart-1": "1.2.3", "chart-2": "4.5.6"}
    repo_name = "test_repo"
    target_branch = "test-branch"
    token = "this_is_a_token"

    logger = logging.getLogger()
    logger.info("Adding file: %s" % filename)
    logger.error("Could not run command")

    expected_calls = [call(["git", "add", filename])]

    with patch(
        "helm_bot.github.run_cmd",
        return_value={"returncode": 1, "err_msg": "Could not run command"},
    ) as mock_run, pytest.raises(RuntimeError):
        add_commit_push(
            filename,
            charts_to_update,
            chart_info,
            repo_name,
            target_branch,
            token,
        )

        assert mock_run.call_count >= 1
        assert mock_run.call_args_list == expected_calls

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
        mocked_func.assert_called_with(
            pr_url,
            headers={"Authorization": f"token {token}"},
            json={"labels": labels},
        )

        capture.check_present()


@log_capture()
def test_assign_reviewers(capture):
    reviewers = ["reviewer1", "reviewer2"]
    url = "http://jsonplaceholder.typicode.com/pulls/1"
    token = "this_is_a_token"

    logger = logging.getLogger()
    logger.info("Add reviewers to Pull Request: %s" % url)
    logger.info("Adding reviewers: %s" % reviewers)

    with patch("helm_bot.github.post_request") as mocked_func:
        assign_reviewers(reviewers, url, token)

        assert mocked_func.call_count == 1
        mocked_func.assert_called_with(
            url + "/requested_reviewers",
            headers={"Authorization": f"token {token}"},
            json={"reviewers": reviewers},
        )

        capture.check_present()


@patch(
    "helm_bot.github.get_request",
    return_value=[{"name": "test_repo1"}, {"name": "test_repo2"}],
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
        json=True,
    )


@responses.activate
@log_capture()
def test_delete_old_branch_does_not_exist(capture):
    repo_name = "test_repo"
    target_branch = "test_branch"
    token = "this_is_a_token"

    logger = logging.getLogger()
    logger.info("Branch does not exist: %s" % target_branch)

    with patch(
        "helm_bot.github.get_request",
        return_value=[{"name": "branch-1"}, {"name": "branch-2"}],
    ) as mocked_func:
        delete_old_branch(repo_name, target_branch, token)

        assert mocked_func.call_count == 1
        mocked_func.assert_called_with(
            f"https://api.github.com/repos/HelmUpgradeBot/{repo_name}/branches",
            headers={"Authorization": f"token {token}"},
            json=True,
        )

        capture.check_present()


@responses.activate
@log_capture()
def test_delete_old_branch_does_exist(capture):
    repo_name = "test_repo"
    target_branch = "test_branch"
    token = "this_is_a_token"

    expected_calls = [
        call(["git", "push", "--delete", "origin", target_branch]),
        call(["git", "branch", "-d", target_branch]),
    ]

    logger = logging.getLogger()
    logger.info("Deleting branch: %s" % target_branch)
    logger.info("Successfully deleted remote branch")
    logger.info("Successfully deleted local branch")

    mock_get = patch(
        "helm_bot.github.get_request",
        return_value=[{"name": "branch-1"}, {"name": target_branch}],
    )
    mock_run = patch("helm_bot.github.run_cmd", return_value={"returncode": 0})

    with mock_get as mock1, mock_run as mock2:
        delete_old_branch(repo_name, target_branch, token)

        assert mock1.call_count == 1
        assert mock2.call_count == 2
        mock1.assert_called_with(
            f"https://api.github.com/repos/HelmUpgradeBot/{repo_name}/branches",
            headers={"Authorization": f"token {token}"},
            json=True,
        )
        assert mock2.call_args_list == expected_calls

        capture.check_present()


@responses.activate
@log_capture()
def test_delete_old_branch_does_exist_exception(capture):
    repo_name = "test_repo"
    target_branch = "test_branch"
    token = "this_is_a_token"

    logger = logging.getLogger()
    logger.info("Deleting branch: %s" % target_branch)
    logger.error("Could not run command")

    expected_call = call(["git", "push", "--delete", "origin", target_branch])

    mock_get = patch(
        "helm_bot.github.get_request",
        return_value=[{"name": "branch-1"}, {"name": target_branch}],
    )
    mock_run = patch(
        "helm_bot.github.run_cmd",
        return_value={"returncode": 1, "err_msg": "Could not run command"},
    )

    with mock_get as mock1, mock_run as mock2, pytest.raises(RuntimeError):
        delete_old_branch(repo_name, target_branch, token)

        assert mock1.call_count == 1
        assert mock2.call_count == 2
        mock1.assert_called_with(
            f"https://api.github.com/repos/HelmUpgradeBot/{repo_name}/branches",
            headers={"Authorization": f"token {token}"},
            json=True,
        )
        assert mock2.call_args == expected_call

        capture.check_present()


@log_capture()
def test_checkout_branch_exists(capture):
    repo_owner = "test_owner"
    repo_name = "test_repo"
    target_branch = "test_branch"
    token = "this_is_a_token"
    pr_exists = False

    logger = logging.getLogger()
    logger.info("Pulling main branch of: %s/%s" % (repo_owner, repo_name))
    logger.info("Successfully pulled main branch")
    logging.info("Checking out branch: %s" % target_branch)
    logger.info("Successfully checked out branch")

    expected_calls = [
        call(
            [
                "git",
                "pull",
                f"https://github.com/{repo_owner}/{repo_name}.git",
                "main",
            ]
        ),
        call(["git", "checkout", "-b", target_branch]),
    ]

    mock_check_fork = patch("helm_bot.github.check_fork_exists", return_value=True)
    # mock_delete_branch = patch("helm_bot.github.delete_old_branch") <-- DEPRECATED
    mock_run_cmd = patch("helm_bot.github.run_cmd", return_value={"returncode": 0})

    with mock_check_fork as mock1, mock_run_cmd as mock2:
        checkout_branch(repo_owner, repo_name, target_branch, token, pr_exists)

        assert mock1.call_count == 1
        assert mock2.call_count == 2
        mock1.assert_called_with(repo_name, token)
        assert mock2.call_args_list == expected_calls

        capture.check_present()


@log_capture()
def test_checkout_branch_exists_exception(capture):
    repo_owner = "test_owner"
    repo_name = "test_repo"
    target_branch = "test_branch"
    token = "this_is_a_token"
    pr_exists = False

    logger = logging.getLogger()
    logger.info("Pulling main branch of: %s/%s" % (repo_owner, repo_name))
    logger.error("Could not run command")

    expected_call = call(
        [
            "git",
            "pull",
            f"https://github.com/{repo_owner}/{repo_name}.git",
            "main",
        ]
    )

    mock_check_fork = patch("helm_bot.github.check_fork_exists", return_value=True)
    mock_delete_branch = patch("helm_bot.github.delete_old_branch")
    mock_run_cmd = patch(
        "helm_bot.github.run_cmd",
        return_value={"returncode": 1, "err_msg": "Could not run command"},
    )

    with mock_check_fork as mock1, mock_delete_branch as mock2, mock_run_cmd as mock3, pytest.raises(
        RuntimeError
    ):
        checkout_branch(repo_owner, repo_name, target_branch, token, pr_exists)

        assert mock1.call_count == 1
        assert mock2.call_count == 1
        assert mock3.call_count >= 1
        mock1.assert_called_with(repo_name, token)
        mock2.assert_called_with(repo_name, target_branch, token)
        assert mock3.call_args == expected_call

        capture.check_present()


@log_capture()
def test_checkout_branch_does_not_exist(capture):
    repo_owner = "test_owner"
    repo_name = "test_repo"
    target_branch = "test_branch"
    token = "this_is_a_token"
    pr_exists = False

    logger = logging.getLogger()
    logging.info("Checking out branch: %s" % target_branch)
    logger.info("Successfully checked out branch")

    expected_call = call(["git", "checkout", "-b", target_branch])

    mock_check_fork = patch("helm_bot.github.check_fork_exists", return_value=False)
    mock_run_cmd = patch("helm_bot.github.run_cmd", return_value={"returncode": 0})

    with mock_check_fork as mock1, mock_run_cmd as mock2:
        checkout_branch(repo_owner, repo_name, target_branch, token, pr_exists)

        assert mock1.call_count == 1
        assert mock2.call_count == 1
        mock1.assert_called_with(repo_name, token)
        assert mock2.call_args == expected_call

        capture.check_present()


@log_capture()
def test_checkout_branch_does_not_exist_exception(capture):
    repo_owner = "test_owner"
    repo_name = "test_repo"
    target_branch = "test_branch"
    token = "this_is_a_token"
    pr_exists = False

    logger = logging.getLogger()
    logger.info("Checking out branch: %s" % target_branch)
    logger.error("Could not run command")

    mock_check_fork = patch("helm_bot.github.check_fork_exists", return_value=False)
    mock_run_cmd = patch(
        "helm_bot.github.run_cmd",
        return_value={"returncode": 1, "err_msg": "Could not run command"},
    )

    with mock_check_fork as mock1, mock_run_cmd as mock2, pytest.raises(RuntimeError):
        checkout_branch(repo_owner, repo_name, target_branch, token, pr_exists)

        assert mock1.call_count == 1
        assert mock2.call_count == 1
        mock1.assert_called_with(repo_name, token)
        mock2.assert_called_with(["git", "checkout", "-b", target_branch])

        capture.check_present()


@log_capture()
def test_clone_fork(capture):
    repo_name = "test_repo"

    logger = logging.getLogger()
    logger.info("Cloning fork: %s" % repo_name)
    logger.info("Successfully cloned fork")

    with patch("helm_bot.github.run_cmd", return_value={"returncode": 0}) as mock_run:
        clone_fork(repo_name)

        assert mock_run.call_count == 1
        mock_run.assert_called_with(
            [
                "git",
                "clone",
                f"https://github.com/HelmUpgradeBot/{repo_name}.git",
            ]
        )
        capture.check_present()


@log_capture()
def test_clone_fork_exception(capture):
    repo_name = "test_repo"

    logger = logging.getLogger()
    logger.info("Cloning fork: %s" % repo_name)
    logger.error("Could not run command")

    with patch(
        "helm_bot.github.run_cmd",
        return_value={"returncode": 1, "err_msg": "Could not run command"},
    ) as mock_run, pytest.raises(RuntimeError):
        clone_fork(repo_name)

        assert mock_run.call_count == 1
        mock_run.assert_called_with(
            [
                "git",
                "clone",
                f"https://github.com/HelmUpgradeBot/{repo_name}.git",
            ]
        )
        capture.check_present()


@log_capture()
def test_create_pr_no_labels_no_reviewers(capture):
    repo_api = "http://jsonplaceholder.typicode.com/"
    base_branch = "base"
    target_branch = "target"
    token = "this_is_a_token"
    labels = []
    reviewers = []

    expected_pr = {
        "title": "Logging Helm Chart version upgrade",
        "body": "This PR is updating the local Helm Chart to the most recent Chart dependency versions.",
        "base": base_branch,
        "head": f"HelmUpgradeBot:{target_branch}",
    }

    logger = logging.getLogger()
    logger.info("Creating Pull Request")
    logger.info("Pull Request created")

    with patch("helm_bot.github.post_request", return_value={}) as mock_post:
        create_pr(repo_api, base_branch, target_branch, token, labels, reviewers)

        assert mock_post.call_count == 1
        assert mock_post.return_value == {}
        mock_post.assert_called_with(
            repo_api + "pulls",
            headers={"Authorization": f"token {token}"},
            json=expected_pr,
            return_json=True,
        )

        capture.check_present()


@log_capture()
def test_create_pr_with_labels_no_reviewers(capture):
    repo_api = "http://jsonplaceholder.typicode.com/"
    base_branch = "base"
    target_branch = "target"
    token = "this_is_a_token"
    labels = ["label1", "label2"]

    expected_pr = {
        "title": "Logging Helm Chart version upgrade",
        "body": "This PR is updating the local Helm Chart to the most recent Chart dependency versions.",
        "base": base_branch,
        "head": f"HelmUpgradeBot:{target_branch}",
    }

    logger = logging.getLogger()
    logger.info("Creating Pull Request")
    logger.info("Pull Request created")

    mock_post = patch(
        "helm_bot.github.post_request",
        return_value={"issue_url": "http://jsonplaceholder.typicode.com/pr/1"},
    )
    mock_labels = patch("helm_bot.github.add_labels", return_value=None)

    with mock_post as mock1, mock_labels as mock2:
        create_pr(repo_api, base_branch, target_branch, token, labels)

        assert mock1.call_count == 1
        assert mock1.return_value == {
            "issue_url": "http://jsonplaceholder.typicode.com/pr/1"
        }
        mock1.assert_called_with(
            repo_api + "pulls",
            headers={"Authorization": f"token {token}"},
            json=expected_pr,
            return_json=True,
        )
        assert mock2.call_count == 1
        mock2.assert_called_with(
            labels, "http://jsonplaceholder.typicode.com/pr/1", token
        )

        capture.check_present()


@log_capture()
def test_create_pr_with_reviewers_no_labels(capture):
    repo_api = "http://jsonplaceholder.typicode.com/"
    base_branch = "base"
    target_branch = "target"
    token = "this_is_a_token"
    reviewers = ["reviewer1", "reviewer2"]

    expected_pr = {
        "title": "Logging Helm Chart version upgrade",
        "body": "This PR is updating the local Helm Chart to the most recent Chart dependency versions.",
        "base": base_branch,
        "head": f"HelmUpgradeBot:{target_branch}",
    }

    logger = logging.getLogger()
    logger.info("Creating Pull Request")
    logger.info("Pull Request created")

    mock_post = patch(
        "helm_bot.github.post_request",
        return_value={"url": "http://jsonplaceholder.typicode.com/pulls/1"},
    )
    mock_reviewers = patch("helm_bot.github.assign_reviewers", return_value=None)

    with mock_post as mock1, mock_reviewers as mock2:
        create_pr(repo_api, base_branch, target_branch, token, reviewers=reviewers)

        assert mock1.call_count == 1
        assert mock1.return_value == {
            "url": "http://jsonplaceholder.typicode.com/pulls/1"
        }
        mock1.assert_called_with(
            repo_api + "pulls",
            headers={"Authorization": f"token {token}"},
            json=expected_pr,
            return_json=True,
        )
        assert mock2.call_count == 1
        mock2.assert_called_with(
            reviewers, "http://jsonplaceholder.typicode.com/pulls/1", token
        )

        capture.check_present()


@log_capture()
def test_create_pr_with_labels_and_reviewers(capture):
    repo_api = "http://jsonplaceholder.typicode.com/"
    base_branch = "base"
    target_branch = "target"
    token = "this_is_a_token"
    labels = ["label1", "label2"]
    reviewers = ["reviewer1", "reviewer2"]

    expected_pr = {
        "title": "Logging Helm Chart version upgrade",
        "body": "This PR is updating the local Helm Chart to the most recent Chart dependency versions.",
        "base": base_branch,
        "head": f"HelmUpgradeBot:{target_branch}",
    }

    logger = logging.getLogger()
    logger.info("Creating Pull Request")
    logger.info("Pull Request created")

    mock_post = patch(
        "helm_bot.github.post_request",
        return_value={
            "issue_url": "http://jsonplaceholder.typicode.com/pr/1",
            "url": "http://jsonplaceholder.typicode.com/pulls/1",
        },
    )
    mock_labels = patch("helm_bot.github.add_labels", return_value=None)
    mock_reviewers = patch("helm_bot.github.assign_reviewers", return_value=None)

    with mock_post as mock1, mock_labels as mock2, mock_reviewers as mock3:
        create_pr(repo_api, base_branch, target_branch, token, labels, reviewers)

        assert mock1.call_count == 1
        assert mock1.return_value == {
            "issue_url": "http://jsonplaceholder.typicode.com/pr/1",
            "url": "http://jsonplaceholder.typicode.com/pulls/1",
        }
        mock1.assert_called_with(
            repo_api + "pulls",
            headers={"Authorization": f"token {token}"},
            json=expected_pr,
            return_json=True,
        )
        assert mock2.call_count == 1
        mock2.assert_called_with(
            labels, "http://jsonplaceholder.typicode.com/pr/1", token
        )
        assert mock3.call_count == 1
        mock3.assert_called_with(
            reviewers, "http://jsonplaceholder.typicode.com/pulls/1", token
        )

        capture.check_present()


@log_capture()
def test_make_fork(capture):
    repo_name = "test_repo"
    repo_api = "http://jsonplaceholder.typicode.com/"
    token = "this_is_a_token"

    logger = logging.getLogger()
    logger.info("Forking repo: %s" % repo_name)
    logger.info("Created fork")

    with patch("helm_bot.github.post_request") as mock_post:
        out = make_fork(repo_name, repo_api, token)

        assert out
        assert mock_post.call_count == 1
        mock_post.assert_called_with(
            repo_api + "forks", headers={"Authorization": f"token {token}"}
        )

        capture.check_present()


@log_capture()
def test_remove_fork_does_not_exist(capture):
    repo_name = "test_repo"
    token = "This_is_a_token"

    logger = logging.getLogger()
    logger.info("HelmUpgradeBot does not have a fork of: %s" % repo_name)

    with patch("helm_bot.github.check_fork_exists", return_value=False) as mock_check:
        out = remove_fork(repo_name, token)

        assert not out
        assert mock_check.call_count == 1
        assert not mock_check.return_value
        mock_check.assert_called_with(repo_name, token)

        capture.check_present()


@log_capture()
def test_remove_fork_exists(capture):
    repo_name = "test_repo"
    token = "this_is_a_token"

    logger = logging.getLogger()
    logger.info("HelmUpgradeBot has a fork of: %s" % repo_name)
    logger.info("Deleted fork")

    mock_check = patch("helm_bot.github.check_fork_exists", return_value=True)
    mock_delete = patch("helm_bot.github.delete_request")
    mock_sleep = patch("helm_bot.github.time.sleep")

    with mock_check as mock1, mock_delete as mock2, mock_sleep as mock3:
        out = remove_fork(repo_name, token)

        assert not out
        assert mock1.return_value
        assert mock1.call_count == 1
        assert mock2.call_count == 1
        assert mock3.call_count == 1
        mock1.assert_called_with(repo_name, token)
        mock2.assert_called_with(
            f"https://api.github.com/repos/HelmUpgradeBot/{repo_name}",
            headers={"Authorization": f"token {token}"},
        )
        mock3.assert_called_with(5)

        capture.check_present()


@log_capture()
def test_set_git_config(capture):
    logger = logging.getLogger()
    logger.info("Setting up GitHub configuration for HelmUpgradeBot")

    expected_calls = [
        call(["git", "config", "--global", "user.name", "HelmUpgradeBot"]),
        call(
            [
                "git",
                "config",
                "--global",
                "user.email",
                "helmupgradebot.github@gmail.com",
            ]
        ),
    ]

    with patch("helm_bot.github.check_call") as mock_check_call:
        set_git_config()

        assert mock_check_call.call_count == 2
        assert mock_check_call.call_args_list == expected_calls

        capture.check_present()
