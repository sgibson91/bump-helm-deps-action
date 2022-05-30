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
            {"some_chart": "https://some-chart.com"},
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
            {"some_chart": "https://some-chart.com"},
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
            {"some_chart": "https://some-chart.com"},
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


if __name__ == "__main__":
    unittest.main()
