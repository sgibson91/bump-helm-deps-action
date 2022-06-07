import base64
import unittest
from unittest.mock import call, patch

from helm_bot.github_api import GitHubAPI
from helm_bot.main import UpdateHelmDeps
from helm_bot.yaml_parser import YamlParser

yaml = YamlParser()


class TestGitHubAPI(unittest.TestCase):
    def test_assign_labels(self):
        helm_deps = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_A_t0k3n",
            "chart-name/Chart.yaml",
            {"some_chart": "https://some-chart.com"},
            labels=["label1", "label2"],
        )
        github = GitHubAPI(helm_deps)
        pr_url = "/".join([github.api_url, "issues", "1"])

        with patch("helm_bot.github_api.post_request") as mock:
            github._assign_labels(pr_url)

            self.assertEqual(mock.call_count, 1)
            mock.assert_called_with(
                "/".join([pr_url, "labels"]),
                headers=helm_deps.headers,
                json={"labels": helm_deps.labels},
            )

    def test_assign_reviewers(self):
        helm_deps = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_A_t0k3n",
            "chart_name/Chart.yaml",
            {"some_chart": "https://some-chart.com"},
            reviewers=["reviewer1", "reviewer2"],
        )
        github = GitHubAPI(helm_deps)
        pr_url = "/".join([github.api_url, "pull", "1"])

        with patch("helm_bot.github_api.post_request") as mock:
            github._assign_reviewers(pr_url)

            self.assertEqual(mock.call_count, 1)
            mock.assert_called_with(
                "/".join([pr_url, "requested_reviewers"]),
                headers=helm_deps.headers,
                json={"reviewers": helm_deps.reviewers},
            )

    def test_assign_team_reviewers(self):
        helm_deps = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_A_t0k3n",
            "chart_name/Chart.yaml",
            {"some_chart": "https://some-chart.com"},
            team_reviewers=["team1", "team2"],
        )
        github = GitHubAPI(helm_deps)
        pr_url = "/".join([github.api_url, "pull", "1"])

        with patch("helm_bot.github_api.post_request") as mock:
            github._assign_reviewers(pr_url)

            self.assertEqual(mock.call_count, 1)
            mock.assert_called_with(
                "/".join([pr_url, "requested_reviewers"]),
                headers=helm_deps.headers,
                json={"team_reviewers": helm_deps.team_reviewers},
            )

    def test_create_commit(self):
        helm_deps = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_A_t0k3n",
            "chart-name/Chart.yaml",
            {"some_chart": "https://some-chart.com"},
        )
        github = GitHubAPI(helm_deps)

        helm_deps.sha = "test_sha"
        commit_msg = "This is a commit message"
        contents = {"key1": "This is a test"}

        contents = yaml.object_to_yaml_str(contents).encode("utf-8")
        contents = base64.b64encode(contents)
        contents = contents.decode("utf-8")

        body = {
            "message": commit_msg,
            "content": contents,
            "sha": helm_deps.sha,
            "branch": helm_deps.head_branch,
        }

        with patch("helm_bot.github_api.put") as mock:
            github.create_commit(
                commit_msg,
                contents,
            )

            self.assertEqual(mock.call_count, 1)
            mock.assert_called_with(
                "/".join([github.api_url, "contents", helm_deps.chart_path]),
                json=body,
                headers=helm_deps.headers,
            )

    def test_create_update_pull_request_no_labels_no_reviewers(self):
        helm_deps = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_A_t0k3n",
            "chart-name/Chart.yaml",
            {"some_chart": "https://some-chart.com"},
        )
        github = GitHubAPI(helm_deps)
        helm_deps.chart_name = "chart-name"
        github.pr_exists = False

        helm_deps.chart_versions = {
            "chart1": {"current": "1.2.3", "latest": "7.8.9"},
            "chart2": {"current": "4.5.6", "latest": "10.11.12"},
        }
        helm_deps.charts_to_update = ["chart1", "chart2"]

        expected_pr = {
            "title": f"Bumping helm chart dependency versions: {helm_deps.chart_name}",
            "body": (
                f"This Pull Request is bumping the dependencies of the `{helm_deps.chart_name}` chart to the following versions.\n\n"
                + "\n".join(
                    [
                        f"- {chart}: `{helm_deps.chart_versions[chart]['current']}` -> `{helm_deps.chart_versions[chart]['latest']}`"
                        for chart in helm_deps.charts_to_update
                    ]
                )
            ),
            "base": helm_deps.base_branch,
            "head": helm_deps.head_branch,
        }

        with patch("helm_bot.github_api.post_request") as mock:
            github.create_update_pull_request()

            self.assertEqual(mock.call_count, 1)
            mock.assert_called_with(
                "/".join([github.api_url, "pulls"]),
                headers=helm_deps.headers,
                json=expected_pr,
                return_json=True,
            )

    def test_create_update_pull_request_with_labels_no_reviewers(self):
        helm_deps = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_A_t0k3n",
            "chart-name/Chart.yaml",
            {"some_chart": "https://some-chart.com"},
            labels=["label1", "label2"],
        )
        github = GitHubAPI(helm_deps)
        helm_deps.chart_name = "chart-name"
        github.pr_exists = False

        helm_deps.chart_versions = {
            "chart1": {"current": "1.2.3", "latest": "7.8.9"},
            "chart2": {"current": "4.5.6", "latest": "10.11.12"},
        }
        helm_deps.charts_to_update = ["chart1", "chart2"]

        expected_pr = {
            "title": f"Bumping helm chart dependency versions: {helm_deps.chart_name}",
            "body": (
                f"This Pull Request is bumping the dependencies of the `{helm_deps.chart_name}` chart to the following versions.\n\n"
                + "\n".join(
                    [
                        f"- {chart}: `{helm_deps.chart_versions[chart]['current']}` -> `{helm_deps.chart_versions[chart]['latest']}`"
                        for chart in helm_deps.charts_to_update
                    ]
                )
            ),
            "base": helm_deps.base_branch,
            "head": helm_deps.head_branch,
        }

        mock_post = patch(
            "helm_bot.github_api.post_request",
            return_value={
                "issue_url": "/".join([github.api_url, "issues", "1"]),
                "number": 1,
            },
        )

        calls = [
            call(
                "/".join([github.api_url, "pulls"]),
                headers=helm_deps.headers,
                json=expected_pr,
                return_json=True,
            ),
            call(
                "/".join([github.api_url, "issues", "1", "labels"]),
                headers=helm_deps.headers,
                json={"labels": helm_deps.labels},
            ),
        ]

        with mock_post as mock:
            github.create_update_pull_request()

            self.assertEqual(mock.call_count, 2)
            self.assertDictEqual(
                mock.return_value,
                {
                    "issue_url": "/".join([github.api_url, "issues", "1"]),
                    "number": 1,
                },
            )
            mock.assert_has_calls(calls)

    def test_create_update_pull_request_no_labels_with_reviewers(self):
        helm_deps = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_A_t0k3n",
            "chart-name/Chart.yaml",
            {"some_chart": "https://some-chart.com"},
            reviewers=["reviewer1", "reviewer2"],
        )
        github = GitHubAPI(helm_deps)
        helm_deps.chart_name = "chart-name"
        github.pr_exists = False

        helm_deps.chart_versions = {
            "chart1": {"current": "1.2.3", "latest": "7.8.9"},
            "chart2": {"current": "4.5.6", "latest": "10.11.12"},
        }
        helm_deps.charts_to_update = ["chart1", "chart2"]

        expected_pr = {
            "title": f"Bumping helm chart dependency versions: {helm_deps.chart_name}",
            "body": (
                f"This Pull Request is bumping the dependencies of the `{helm_deps.chart_name}` chart to the following versions.\n\n"
                + "\n".join(
                    [
                        f"- {chart}: `{helm_deps.chart_versions[chart]['current']}` -> `{helm_deps.chart_versions[chart]['latest']}`"
                        for chart in helm_deps.charts_to_update
                    ]
                )
            ),
            "base": helm_deps.base_branch,
            "head": helm_deps.head_branch,
        }

        mock_post = patch(
            "helm_bot.github_api.post_request",
            return_value={
                "url": "/".join([github.api_url, "pulls", "1"]),
                "number": 1,
            },
        )

        calls = [
            call(
                "/".join([github.api_url, "pulls"]),
                headers=helm_deps.headers,
                json=expected_pr,
                return_json=True,
            ),
            call(
                "/".join([github.api_url, "pulls", "1", "requested_reviewers"]),
                headers=helm_deps.headers,
                json={"reviewers": helm_deps.reviewers},
            ),
        ]

        with mock_post as mock:
            github.create_update_pull_request()

            self.assertEqual(mock.call_count, 2)
            self.assertDictEqual(
                mock.return_value,
                {
                    "url": "/".join([github.api_url, "pulls", "1"]),
                    "number": 1,
                },
            )
            mock.assert_has_calls(calls)

    def test_create_update_pull_request_with_labels_and_reviewers(self):
        helm_deps = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_A_t0k3n",
            "chart-name/Chart.yaml",
            {"some_chart": "https://some-chart.com"},
            labels=["label1", "label2"],
            reviewers=["reviewer1", "reviewer2"],
        )
        github = GitHubAPI(helm_deps)
        helm_deps.chart_name = "chart-name"
        github.pr_exists = False

        helm_deps.chart_versions = {
            "chart1": {"current": "1.2.3", "latest": "7.8.9"},
            "chart2": {"current": "4.5.6", "latest": "10.11.12"},
        }
        helm_deps.charts_to_update = ["chart1", "chart2"]

        expected_pr = {
            "title": f"Bumping helm chart dependency versions: {helm_deps.chart_name}",
            "body": (
                f"This Pull Request is bumping the dependencies of the `{helm_deps.chart_name}` chart to the following versions.\n\n"
                + "\n".join(
                    [
                        f"- {chart}: `{helm_deps.chart_versions[chart]['current']}` -> `{helm_deps.chart_versions[chart]['latest']}`"
                        for chart in helm_deps.charts_to_update
                    ]
                )
            ),
            "base": helm_deps.base_branch,
            "head": helm_deps.head_branch,
        }

        mock_post = patch(
            "helm_bot.github_api.post_request",
            return_value={
                "issue_url": "/".join([github.api_url, "issues", "1"]),
                "url": "/".join([github.api_url, "pulls", "1"]),
                "number": 1,
            },
        )

        calls = [
            call(
                "/".join([github.api_url, "pulls"]),
                headers=helm_deps.headers,
                json=expected_pr,
                return_json=True,
            ),
            call(
                "/".join([github.api_url, "issues", "1", "labels"]),
                headers=helm_deps.headers,
                json={"labels": helm_deps.labels},
            ),
            call(
                "/".join([github.api_url, "pulls", "1", "requested_reviewers"]),
                headers=helm_deps.headers,
                json={"reviewers": helm_deps.reviewers},
            ),
        ]

        with mock_post as mock:
            github.create_update_pull_request()

            self.assertEqual(mock.call_count, 3)
            self.assertDictEqual(
                mock.return_value,
                {
                    "issue_url": "/".join([github.api_url, "issues", "1"]),
                    "url": "/".join([github.api_url, "pulls", "1"]),
                    "number": 1,
                },
            )
            mock.assert_has_calls(calls)

    def test_create_ref(self):
        helm_deps = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_A_t0k3n",
            "chart-name/Chart.yaml",
            {"some_chart": "https://some-chart.com"},
        )
        github = GitHubAPI(helm_deps)
        test_ref = "test_ref"
        test_sha = "test_sha"

        test_body = {"ref": f"refs/heads/{test_ref}", "sha": test_sha}

        with patch("helm_bot.github_api.post_request") as mock:
            github.create_ref(test_ref, test_sha)

            self.assertEqual(mock.call_count, 1)
            mock.assert_called_with(
                "/".join([github.api_url, "git", "refs"]),
                headers=helm_deps.headers,
                json=test_body,
            )

    def test_find_existing_pull_request_no_matches(self):
        helm_deps = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_A_t0k3n",
            "chart-name/Chart.yaml",
            {"some_chart": "https://some-chart.com"},
        )
        github = GitHubAPI(helm_deps)

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
            github.find_existing_pull_request()

            self.assertEqual(mock.call_count, 1)
            mock.assert_called_with(
                "/".join([github.api_url, "pulls"]),
                headers=helm_deps.headers,
                params={"state": "open", "sort": "created", "direction": "desc"},
                output="json",
            )
            self.assertFalse(github.pr_exists)
            self.assertTrue(
                helm_deps.head_branch.startswith(
                    "/".join(["bump-helm-deps", "chart-name"])
                )
            )

    def test_find_existing_pull_request_match(self):
        helm_deps = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_A_t0k3n",
            "chart-name/Chart.yaml",
            {"some_chart": "https://some-chart.com"},
        )
        github = GitHubAPI(helm_deps)

        mock_get = patch(
            "helm_bot.github_api.get_request",
            return_value=[
                {
                    "head": {
                        "label": "bump-helm-deps/chart-name",
                    },
                    "number": 1,
                }
            ],
        )

        with mock_get as mock:
            github.find_existing_pull_request()

            self.assertEqual(mock.call_count, 1)
            mock.assert_called_with(
                "/".join([github.api_url, "pulls"]),
                headers=helm_deps.headers,
                params={"state": "open", "sort": "created", "direction": "desc"},
                output="json",
            )
            self.assertTrue(github.pr_exists)
            self.assertEqual(
                helm_deps.head_branch, "/".join(["bump-helm-deps", "chart-name"])
            )
            self.assertEqual(github.pr_number, 1)

    def test_get_ref(self):
        helm_deps = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_A_t0k3n",
            "chart-name/Chart.yaml",
            {"some_chart": "https://some-chart.com"},
        )
        github = GitHubAPI(helm_deps)
        test_ref = "test_ref"

        mock_get = patch(
            "helm_bot.github_api.get_request", return_value={"object": {"sha": "sha"}}
        )

        with mock_get as mock:
            resp = github.get_ref(test_ref)

            self.assertEqual(mock.call_count, 1)
            mock.assert_called_with(
                "/".join([github.api_url, "git", "ref", "heads", test_ref]),
                headers=helm_deps.headers,
                output="json",
            )
            self.assertDictEqual(resp, {"object": {"sha": "sha"}})

    def test_update_existing_pr(self):
        helm_deps = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_A_t0k3n",
            "chart-name/Chart.yaml",
            {"some_chart": "https://some-chart.com"},
        )
        github = GitHubAPI(helm_deps)
        github.pr_exists = True
        github.pr_number = 1
        helm_deps.chart_versions = {
            "chart": {"current": "old_version", "latest": "new_version"},
        }
        helm_deps.charts_to_update = ["chart"]
        helm_deps.chart_name = "chart-name"

        expected_pr = {
            "title": f"Bumping helm chart dependency versions: {helm_deps.chart_name}",
            "body": (
                f"This Pull Request is bumping the dependencies of the `{helm_deps.chart_name}` chart to the following versions.\n\n"
                + "\n".join(
                    [
                        f"- {chart}: `{helm_deps.chart_versions[chart]['current']}` -> `{helm_deps.chart_versions[chart]['latest']}`"
                        for chart in helm_deps.charts_to_update
                    ]
                )
            ),
            "base": helm_deps.base_branch,
            "state": "open",
        }

        mock_patch = patch(
            "helm_bot.github_api.patch_request", return_value={"number": 1}
        )

        with mock_patch as mock:
            github.create_update_pull_request()

            mock.assert_called_with(
                "/".join([github.api_url, "pulls", str(github.pr_number)]),
                headers=helm_deps.headers,
                json=expected_pr,
                return_json=True,
            )
            self.assertDictEqual(mock.return_value, {"number": 1})


if __name__ == "__main__":
    unittest.main()
