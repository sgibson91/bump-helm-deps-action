import warnings
from itertools import compress

from loguru import logger

from .http_requests import get_request
from .yaml_parser import YamlParser

yaml = YamlParser()


class HelmChartVersionPuller:
    """
    Check the versions of subcharts in a local helm chart against the most recently
    published version and update if needed.
    """

    def __init__(self, inputs, branch):
        self.inputs = inputs
        self.branch = branch
        self.github_api_url = "/".join(
            ["https://api.github.com", "repos", self.inputs.repository]
        )
        self.chart_versions = {}

    def _get_config(self, ref):
        """Get the contents and sha of a YAML config file in a GitHub repo over the API

        Args:
            ref (str): The reference (branch) the file is stored on

        Returns:
            config (dict): The config stored at the provided filepath
            sha (str): The SHA of the file
        """
        url = "/".join([self.github_api_url, "contents", self.inputs.chart_path])
        query = {"ref": ref}
        resp = get_request(
            url, headers=self.inputs.headers, params=query, output="json"
        )

        download_url = resp["download_url"]
        sha = resp["sha"]

        resp = get_request(download_url, headers=self.inputs.headers, output="text")
        return yaml.yaml_string_to_object(resp), sha

    def _pull_version_github_pages(self, chart, chart_url):
        """Pull helm chart dependencies and versions from remote host listed on a
        GitHub Pages site.

        Args:
            chart (str): The name of the helm chart dependency to pull
                versions for.
            chart_url (str): The URL of the remotely hosted helm chart dependencies
        """
        releases = yaml.yaml_string_to_object(
            get_request(chart_url, headers=self.inputs.headers, output="text")
        )
        releases_sorted = sorted(releases["entries"][chart], key=lambda k: k["created"])
        self.chart_versions[chart]["latest"] = releases_sorted[-1]["version"]

    def _get_remote_versions(self):
        """
        Decipher where a list of chart versions is hosted and find the most recently
        published version
        """
        logger.info("Fetching most recently published helm chart versions...")
        for chart, chart_url in self.inputs.chart_urls.items():
            if "/gh-pages/" in chart_url:
                self._pull_version_github_pages(chart, chart_url)
            else:
                warnings.warn(
                    f"NotImplemented: Cannot currently retrieve version from URL type: {chart_url}"
                )
                continue

    def _compare_chart_versions(self):
        """Compare the current helm chart dependencies against the most recently
        available and ascertain if a subchart can be updated

        Returns:
            charts_to_update (list): A list of the helm chart dependencies that need
                updating
        """
        condition = [
            (
                self.chart_versions[chart]["current"]
                != self.chart_versions[chart]["latest"]
            )
            for chart in self.chart_versions.keys()
        ]
        return list(compress(self.chart_versions.keys(), condition))

    def get_chart_versions(self):
        """Get the versions of dependent helm charts"""
        logger.info("Fetching current subchart versions from helm chart...")
        self.inputs.chart_yaml, self.inputs.sha = self._get_config(self.branch)
        self.inputs.chart_name = (
            self.inputs.chart_yaml["name"]
            if "name" in self.inputs.chart_yaml.keys()
            else self.inputs.chart_path.split("/")[-2]
        )

        for chart in self.inputs.chart_yaml["dependencies"]:
            self.chart_versions[chart["name"]] = {"current": chart["version"]}

        self._get_remote_versions()
        self.inputs.charts_to_update = self._compare_chart_versions()
        self.inputs.chart_versions = self.chart_versions
