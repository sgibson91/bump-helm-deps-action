import base64
from unittest.mock import patch

import yaml

from helm_bot.github_api import (
    add_labels,
    assign_reviewers,
    create_commit,
    create_ref,
    create_update_pr,
    find_existing_pr,
    get_contents,
    get_ref,
)

test_url = "http://jsonplaceholder.typicode.com"
test_header = {"Authorization": "token ThIs_Is_A_ToKeN"}


def test_add_labels():
    test_labels = ["label1", "label2"]

    with patch("helm_bot.github_api.post_request") as mocked_func:
        add_labels(test_labels, test_url, test_header)

        assert mocked_func.call_count == 1
        mocked_func.assert_called_with(
            test_url, headers=test_header, json={"labels": test_labels}
        )


def test_assign_reviewers():
    test_reviewers = ["reviewer1", "reviewer2"]

    with patch("helm_bot.github_api.post_request") as mocked_func:
        assign_reviewers(test_reviewers, [], test_url, test_header)

        assert mocked_func.call_count == 1
        mocked_func.assert_called_with(
            "/".join([test_url, "requested_reviewers"]),
            headers=test_header,
            json={"reviewers": test_reviewers, "team_reviewers": []},
        )


def test_create_commit():
    test_path = "config/test_config.yaml"
    test_branch = "test_branch"
    test_sha = "test_sha"
    test_commit_msg = "This is a commit message"

    test_contents = {"key1": "This is a test"}
    test_contents = yaml.safe_dump(test_contents).encode("utf-8")
    test_contents = base64.b64encode(test_contents)
    test_contents = test_contents.decode("utf-8")

    test_body = {
        "message": test_commit_msg,
        "content": test_contents,
        "sha": test_sha,
        "branch": test_branch,
    }

    with patch("helm_bot.github_api.put") as mocked_func:
        create_commit(
            test_url,
            test_header,
            test_path,
            test_branch,
            test_sha,
            test_commit_msg,
            test_contents,
        )

        assert mocked_func.call_count == 1
        mocked_func.assert_called_with(
            "/".join([test_url, "contents", test_path]),
            json=test_body,
            headers=test_header,
        )


def test_create_update_pr_no_labels_no_reviewers():
    test_base_branch = "main"
    test_head_branch = "head"
    test_chart_name = "test-chart"
    test_chart_info = {
        test_chart_name: {"chart1": "1.2.3", "chart2": "4.5.6"},
        "chart1": "7.8.9",
        "chart2": "10.11.12",
    }
    test_charts_to_update = ["chart1", "chart2"]
    test_labels = []
    test_reviewers = []
    test_team_reviewers = []

    expected_pr = {
        "title": f"Bumping helm chart dependency versions: {test_chart_name}",
        "body": (
            f"This Pull Request is bumping the dependencies of the `{test_chart_name}` chart to the following versions.\n\n"
            + "\n".join(
                [
                    f"- {chart}: `{test_chart_info[test_chart_name][chart]}` -> `{test_chart_info[chart]}`"
                    for chart in test_charts_to_update
                ]
            )
        ),
        "base": test_base_branch,
        "head": test_head_branch,
    }

    with patch("helm_bot.github_api.post_request") as mocked_func:
        create_update_pr(
            test_url,
            test_header,
            test_base_branch,
            test_head_branch,
            test_chart_name,
            test_chart_info,
            test_charts_to_update,
            labels=test_labels,
            reviewers=test_reviewers,
            team_reviewers=test_team_reviewers,
            pr_exists=False,
        )

        assert mocked_func.call_count == 1
        mocked_func.assert_called_with(
            "/".join([test_url, "pulls"]),
            headers=test_header,
            json=expected_pr,
            return_json=True,
        )


def test_create_update_pr_with_labels_no_reviewers():
    test_base_branch = "main"
    test_head_branch = "head"
    test_chart_name = "test-chart"
    test_chart_info = {
        test_chart_name: {"chart1": "1.2.3", "chart2": "4.5.6"},
        "chart1": "7.8.9",
        "chart2": "10.11.12",
    }
    test_charts_to_update = ["chart1", "chart2"]
    test_labels = ["label1", "label2"]
    test_reviewers = []
    test_team_reviewers = []

    expected_pr = {
        "title": f"Bumping helm chart dependency versions: {test_chart_name}",
        "body": (
            f"This Pull Request is bumping the dependencies of the `{test_chart_name}` chart to the following versions.\n\n"
            + "\n".join(
                [
                    f"- {chart}: `{test_chart_info[test_chart_name][chart]}` -> `{test_chart_info[chart]}`"
                    for chart in test_charts_to_update
                ]
            )
        ),
        "base": test_base_branch,
        "head": test_head_branch,
    }

    mock_post = patch(
        "helm_bot.github_api.post_request",
        return_value={"issue_url": "/".join([test_url, "issues", "1"]), "number": 1},
    )
    mock_labels = patch("helm_bot.github_api.add_labels")

    with mock_post as mock1, mock_labels as mock2:
        create_update_pr(
            test_url,
            test_header,
            test_base_branch,
            test_head_branch,
            test_chart_name,
            test_chart_info,
            test_charts_to_update,
            labels=test_labels,
            reviewers=test_reviewers,
            team_reviewers=test_team_reviewers,
            pr_exists=False,
        )

        assert mock1.call_count == 1
        assert mock1.return_value == {
            "issue_url": "/".join([test_url, "issues", "1"]),
            "number": 1,
        }
        mock1.assert_called_with(
            "/".join([test_url, "pulls"]),
            headers=test_header,
            json=expected_pr,
            return_json=True,
        )
        assert mock2.call_count == 1
        mock2.assert_called_with(
            test_labels, "/".join([test_url, "issues", "1"]), test_header
        )


def test_create_update_pr_no_labels_with_reviewers():
    test_base_branch = "main"
    test_head_branch = "head"
    test_chart_name = "test-chart"
    test_chart_info = {
        test_chart_name: {"chart1": "1.2.3", "chart2": "4.5.6"},
        "chart1": "7.8.9",
        "chart2": "10.11.12",
    }
    test_charts_to_update = ["chart1", "chart2"]
    test_labels = []
    test_reviewers = ["reviewer1", "reviewer2"]
    test_team_reviewers = []

    expected_pr = {
        "title": f"Bumping helm chart dependency versions: {test_chart_name}",
        "body": (
            f"This Pull Request is bumping the dependencies of the `{test_chart_name}` chart to the following versions.\n\n"
            + "\n".join(
                [
                    f"- {chart}: `{test_chart_info[test_chart_name][chart]}` -> `{test_chart_info[chart]}`"
                    for chart in test_charts_to_update
                ]
            )
        ),
        "base": test_base_branch,
        "head": test_head_branch,
    }

    mock_post = patch(
        "helm_bot.github_api.post_request",
        return_value={"url": "/".join([test_url, "pulls", "1"]), "number": 1},
    )
    mock_reviewers = patch("helm_bot.github_api.assign_reviewers")

    with mock_post as mock1, mock_reviewers as mock2:
        create_update_pr(
            test_url,
            test_header,
            test_base_branch,
            test_head_branch,
            test_chart_name,
            test_chart_info,
            test_charts_to_update,
            labels=test_labels,
            reviewers=test_reviewers,
            team_reviewers=test_team_reviewers,
            pr_exists=False,
        )

        assert mock1.call_count == 1
        assert mock1.return_value == {
            "url": "/".join([test_url, "pulls", "1"]),
            "number": 1,
        }
        mock1.assert_called_with(
            "/".join([test_url, "pulls"]),
            headers=test_header,
            json=expected_pr,
            return_json=True,
        )
        assert mock2.call_count == 1
        mock2.assert_called_with(
            test_reviewers,
            test_team_reviewers,
            "/".join([test_url, "pulls", "1"]),
            test_header,
        )


def test_create_update_pr_with_labels_and_reviewers():
    test_base_branch = "main"
    test_head_branch = "head"
    test_chart_name = "test-chart"
    test_chart_info = {
        test_chart_name: {"chart1": "1.2.3", "chart2": "4.5.6"},
        "chart1": "7.8.9",
        "chart2": "10.11.12",
    }
    test_charts_to_update = ["chart1", "chart2"]
    test_labels = ["label1", "label2"]
    test_reviewers = ["reviewer1", "reviewer2"]
    test_team_reviewers = []

    expected_pr = {
        "title": f"Bumping helm chart dependency versions: {test_chart_name}",
        "body": (
            f"This Pull Request is bumping the dependencies of the `{test_chart_name}` chart to the following versions.\n\n"
            + "\n".join(
                [
                    f"- {chart}: `{test_chart_info[test_chart_name][chart]}` -> `{test_chart_info[chart]}`"
                    for chart in test_charts_to_update
                ]
            )
        ),
        "base": test_base_branch,
        "head": test_head_branch,
    }

    mock_post = patch(
        "helm_bot.github_api.post_request",
        return_value={
            "issue_url": "/".join([test_url, "issues", "1"]),
            "url": "/".join([test_url, "pulls", "1"]),
            "number": 1,
        },
    )
    mock_labels = patch("helm_bot.github_api.add_labels")
    mock_reviewers = patch("helm_bot.github_api.assign_reviewers")

    with mock_post as mock1, mock_labels as mock2, mock_reviewers as mock3:
        create_update_pr(
            test_url,
            test_header,
            test_base_branch,
            test_head_branch,
            test_chart_name,
            test_chart_info,
            test_charts_to_update,
            labels=test_labels,
            reviewers=test_reviewers,
            team_reviewers=test_team_reviewers,
            pr_exists=False,
        )

        assert mock1.call_count == 1
        assert mock1.return_value == {
            "issue_url": "/".join([test_url, "issues", "1"]),
            "url": "/".join([test_url, "pulls", "1"]),
            "number": 1,
        }
        mock1.assert_called_with(
            "/".join([test_url, "pulls"]),
            headers=test_header,
            json=expected_pr,
            return_json=True,
        )
        assert mock2.call_count == 1
        mock2.assert_called_with(
            test_labels, "/".join([test_url, "issues", "1"]), test_header
        )
        assert mock3.call_count == 1
        mock3.assert_called_with(
            test_reviewers,
            test_team_reviewers,
            "/".join([test_url, "pulls", "1"]),
            test_header,
        )


def test_create_ref():
    test_ref = "test_ref"
    test_sha = "test_sha"

    test_body = {"ref": f"refs/heads/{test_ref}", "sha": test_sha}

    with patch("helm_bot.github_api.post_request") as mocked_func:
        create_ref(test_url, test_header, test_ref, test_sha)

        assert mocked_func.call_count == 1
        mocked_func.assert_called_with(
            "/".join([test_url, "git", "refs"]),
            headers=test_header,
            json=test_body,
        )


def test_find_existing_pr_no_matches():
    mock_get = patch(
        "helm_bot.github_api.get_request",
        return_value=[
            {
                "head": {
                    "label": "some_branch",
                }
            }
        ],
    )

    with mock_get as mock:
        pr_exists, branch_name = find_existing_pr(test_url, test_header)

        assert mock.call_count == 1
        mock.assert_called_with(
            test_url + "/pulls",
            headers=test_header,
            params={"state": "open", "sort": "created", "direction": "desc"},
            output="json",
        )
        assert not pr_exists
        assert branch_name is None


def test_find_existing_pr_one_match():
    mock_get = patch(
        "helm_bot.github_api.get_request",
        return_value=[
            {
                "head": {
                    "label": "helm_dep_bump",
                }
            }
        ],
    )

    with mock_get as mock:
        pr_exists, branch_name = find_existing_pr(test_url, test_header)

        assert mock.call_count == 1
        mock.assert_called_with(
            test_url + "/pulls",
            headers=test_header,
            params={"state": "open", "sort": "created", "direction": "desc"},
            output="json",
        )
        assert pr_exists
        assert branch_name == "helm_dep_bump"


def test_find_existing_pr_multiple_matches():
    mock_get = patch(
        "helm_bot.github_api.get_request",
        return_value=[
            {
                "head": {
                    "label": "helm_dep_bump1",
                }
            },
            {
                "head": {
                    "label": "helm_dep_bump2",
                }
            },
        ],
    )

    with mock_get as mock:
        pr_exists, branch_name = find_existing_pr(test_url, test_header)

        assert mock.call_count == 1
        mock.assert_called_with(
            test_url + "/pulls",
            headers=test_header,
            params={"state": "open", "sort": "created", "direction": "desc"},
            output="json",
        )
        assert pr_exists
        assert branch_name == "helm_dep_bump1"


def test_get_contents():
    test_path = "config/test_config.yaml"
    test_ref = "test_ref"
    test_query = {"ref": test_ref}

    mock_get = patch(
        "helm_bot.github_api.get_request",
        return_value={
            "download_url": "/".join([test_url, "download", test_path]),
            "sha": "blob_sha",
        },
    )

    with mock_get as mocked_func:
        resp = get_contents(test_url, test_header, test_path, test_ref)

        assert mocked_func.call_count == 1
        mocked_func.assert_called_with(
            "/".join([test_url, "contents", test_path]),
            headers=test_header,
            params=test_query,
            output="json",
        )
        assert resp == {
            "download_url": "/".join([test_url, "download", test_path]),
            "sha": "blob_sha",
        }


def test_get_ref():
    test_ref = "test_ref"

    mock_get = patch(
        "helm_bot.github_api.get_request", return_value={"object": {"sha": "sha"}}
    )

    with mock_get as mock1:
        resp = get_ref(test_url, test_header, test_ref)

        assert mock1.call_count == 1
        mock1.assert_called_with(
            "/".join([test_url, "git", "ref", "heads", test_ref]),
            headers=test_header,
            output="json",
        )
        assert resp == {"object": {"sha": "sha"}}
