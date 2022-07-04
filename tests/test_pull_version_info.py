import unittest
from unittest.mock import patch

from helm_bot.main import UpdateHelmDeps
from helm_bot.pull_version_info import HelmChartVersionPuller


class TestHelmChartVersionPuller(unittest.TestCase):
    def test_compare_chart_versions_match(self):
        helm_deps = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_a_t0k3n",
            "chart-name/Chart.yaml",
            {"some_chart": {"url": "https://some-chart.com"}},
        )
        version_puller = HelmChartVersionPuller(helm_deps, "main")
        version_puller.chart_versions = {
            "some_chart": {
                "current": "version",
                "latest": "version",
            }
        }

        result = version_puller._compare_chart_versions()

        self.assertEqual(result, [])

    def test_compare_chart_versions_no_match(self):
        helm_deps = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_a_t0k3n",
            "chart-name/Chart.yaml",
            {"some_chart": {"url": "https://some-chart.com"}},
        )
        version_puller = HelmChartVersionPuller(helm_deps, "main")
        version_puller.chart_versions = {
            "some_chart": {
                "current": "old_version",
                "latest": "new_version",
            }
        }

        result = version_puller._compare_chart_versions()

        self.assertEqual(result, ["some_chart"])

    @patch("helm_bot.pull_version_info.get_request")
    def test_get_config(self, mock_get):
        helm_deps = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_a_t0k3n",
            "chart-name/Chart.yaml",
            {"some_chart": {"url": "https://some-chart.com"}},
        )
        version_puller = HelmChartVersionPuller(helm_deps, helm_deps.base_branch)

        mock_get.side_effect = [
            {
                "download_url": "https://example.com",
                "sha": "123456789",
            },
            "hello: world",
        ]

        expected_config = {"hello": "world"}
        expected_sha = "123456789"

        config, sha = version_puller._get_config(helm_deps.base_branch)

        self.assertDictEqual(config, expected_config)
        self.assertEqual(sha, expected_sha)

    def test_pull_version_github_pages(self):
        helm_deps = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_A_t0k3n",
            "chart_name/Chart.yaml",
            {"some_chart": {"url": "https://some-chart.com"}},
        )
        versionpuller = HelmChartVersionPuller(helm_deps, helm_deps.base_branch)
        versionpuller.chart_versions = {"some_chart": {"current": "old_version"}}

        expected_chart_versions = {
            "some_chart": {
                "current": "old_version",
                "latest": "new_version",
            }
        }

        mock_get = patch(
            "helm_bot.pull_version_info.get_request",
            return_value="""{
                "entries": {
                    "some_chart": [
                        {
                            "created": "2022-07-04T13:10:00Z",
                            "version": "new_version",
                        }
                    ]
                }
            }""",
        )

        with mock_get as mock:
            versionpuller._pull_version_github_pages(
                "some_chart", helm_deps.chart_info["some_chart"]["url"]
            )

            self.assertEqual(mock.call_count, 1)
            mock.assert_called_with(
                helm_deps.chart_info["some_chart"]["url"],
                headers=helm_deps.headers,
                output="text",
            )
            self.assertDictEqual(versionpuller.chart_versions, expected_chart_versions)

    def test_pull_version_github_pages_regexpr(self):
        helm_deps = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_A_t0k3n",
            "chart_name/Chart.yaml",
            {
                "some_chart": {
                    "url": "https://some-chart.com",
                    "prefix": "some-",
                    "regexpr": r"[0-9]*\.[0-9]*\.[0-9]*",
                }
            },
        )
        versionpuller = HelmChartVersionPuller(helm_deps, helm_deps.base_branch)
        versionpuller.chart_versions = {"some_chart": {"current": "old_version"}}

        expected_chart_versions = {
            "some_chart": {
                "current": "old_version",
                "latest": "1.2.3",
            }
        }

        mock_get = patch(
            "helm_bot.pull_version_info.get_request",
            return_value="""{
                "entries": {
                    "some_chart": [
                        {
                            "created": "2022-07-04T13:10:00Z",
                            "version": "new_version",
                        },
                        {
                            "created": "2022-07-04T13:21:00Z",
                            "version": "7.8.9",
                        },
                        {
                            "created": "2022-07-04T13:10:00Z",
                            "version": "some-1.2.3",
                        },
                    ]
                }
            }""",
        )

        with mock_get as mock:
            versionpuller._pull_version_github_pages(
                "some_chart",
                helm_deps.chart_info["some_chart"]["url"],
                helm_deps.chart_info["some_chart"]["prefix"],
                helm_deps.chart_info["some_chart"]["regexpr"],
            )

            self.assertEqual(mock.call_count, 1)
            mock.assert_called_with(
                helm_deps.chart_info["some_chart"]["url"],
                headers=helm_deps.headers,
                output="text",
            )
            self.assertDictEqual(versionpuller.chart_versions, expected_chart_versions)

    def test_pull_version_github_releases(self):
        helm_deps = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_A_t0k3n",
            "chart_name/Chart.yaml",
            {"some_chart": {"url": "https://github.com/some-org/some_chart/releases"}},
        )
        versionpuller = HelmChartVersionPuller(helm_deps, helm_deps.base_branch)
        versionpuller.chart_versions = {"some_chart": {"current": "old_version"}}

        expected_chart_versions = {
            "some_chart": {
                "current": "old_version",
                "latest": "new_version",
            }
        }

        mock_get = patch(
            "helm_bot.pull_version_info.get_request",
            return_value=[
                {
                    "published_at": "2022-07-04T13:28:00Z",
                    "name": "new_version",
                },
            ],
        )

        with mock_get as mock:
            versionpuller._pull_version_github_releases(
                "some_chart", helm_deps.chart_info["some_chart"]["url"]
            )

            self.assertEqual(mock.call_count, 1)
            mock.assert_called_with(
                helm_deps.chart_info["some_chart"]["url"].replace(
                    "https://github.com", "https://api.github.com/repos"
                ),
                headers=helm_deps.headers,
                params={"per_page": 100},
                output="json",
            )
            self.assertDictEqual(versionpuller.chart_versions, expected_chart_versions)

    def test_pull_version_github_releases_regexpr(self):
        helm_deps = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_A_t0k3n",
            "chart_name/Chart.yaml",
            {
                "some_chart": {
                    "url": "https://github.com/some-org/some-chart/releses",
                    "prefix": "some-",
                    "regexpr": r"[0-9]*\.[0-9]*\.[0-9]*",
                }
            },
        )
        versionpuller = HelmChartVersionPuller(helm_deps, helm_deps.base_branch)
        versionpuller.chart_versions = {"some_chart": {"current": "old_version"}}

        expected_chart_versions = {
            "some_chart": {
                "current": "old_version",
                "latest": "1.2.3",
            }
        }

        mock_get = patch(
            "helm_bot.pull_version_info.get_request",
            return_value=[
                {
                    "published_at": "2022-07-04T13:10:00Z",
                    "name": "new_version",
                },
                {
                    "published_at": "2022-07-04T13:21:00Z",
                    "name": "7.8.9",
                },
                {
                    "published_at": "2022-07-04T13:10:00Z",
                    "name": "some-1.2.3",
                },
            ],
        )

        with mock_get as mock:
            versionpuller._pull_version_github_releases(
                "some_chart",
                helm_deps.chart_info["some_chart"]["url"],
                helm_deps.chart_info["some_chart"]["prefix"],
                helm_deps.chart_info["some_chart"]["regexpr"],
            )

            self.assertEqual(mock.call_count, 1)
            mock.assert_called_with(
                helm_deps.chart_info["some_chart"]["url"].replace(
                    "https://github.com", "https://api.github.com/repos"
                ),
                headers=helm_deps.headers,
                params={"per_page": 100},
                output="json",
            )
            self.assertDictEqual(versionpuller.chart_versions, expected_chart_versions)


if __name__ == "__main__":
    unittest.main()
