import re
import warnings
from datetime import datetime
from itertools import compress

from dateutil.parser import isoparse
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

    def _pull_version_github_pages(self, chart, chart_url, prefix=None, regexpr=None):
        """Pull helm chart versions from remote host listed on a GitHub Pages site

        Args:
            chart (str): The name of the helm chart dependency to pull
                versions for
            chart_url (str): The URL of the remotely hosted helm chart versions
            prefix (str, optional): If filtering for a specific version format, the
                prefix the required format has. E.g. prefix='prometheus' for versions
                matching format 'prometheus-X.Y.Z'. Defaults to None.
            regexpr (str, optional): If filtering for a specific version format, this is
                the regular expression that will match that format. Defaults to None.
                If prefix is not None, the full regexpr will be prefix+regexpr.
        """
        releases = yaml.yaml_string_to_object(
            get_request(chart_url, headers=self.inputs.headers, output="text")
        )

        for release in releases["entries"][chart]:
            release["created"] = isoparse(release["created"])

        releases = sorted(releases["entries"][chart], key=lambda k: k["created"])

        if regexpr is not None:
            print(regexpr)
            prefix = "" if prefix is None else prefix
            print(prefix)
            print(f"{prefix}{regexpr}")
            pattern = re.compile(f"{prefix}{regexpr}")
            releases = [
                release
                for release in releases
                if pattern.match(release["version"]) is not None
            ]

        latest_release = releases[-1]["version"]

        if regexpr is not None:
            latest_release = re.search(regexpr, latest_release)
            self.chart_versions[chart]["latest"] = latest_release.group()
        else:
            self.chart_versions[chart]["latest"] = latest_release

    def _pull_version_github_releases(
        self, chart, chart_url, prefix=None, regexpr=None
    ):
        """Pull helm chart versions from remote host listed on a GitHub Releases page

        Args:
            chart (str): The name of the helm chart dependency to pull
                versions for
            chart_url (str): The URL of the remotely hosted helm chart versions
            prefix (str, optional): If filtering for a specific version format, the
                prefix the required format has. E.g. prefix='prometheus' for versions
                matching format 'prometheus-X.Y.Z'. Defaults to None.
            regexpr (str, optional): If filtering for a specific version format, this is
                the regular expression that will match that format. Defaults to None.
                If prefix is not None, the full regexpr will be prefix+regexpr.
        """
        url = chart_url.replace("https://github.com", "https://api.github.com/repos")
        releases = get_request(
            url, headers=self.inputs.headers, params={"per_page": 100}, output="json"
        )

        for release in releases:
            release["published_at"] = isoparse(release["published_at"])

        releases = sorted(releases, key=lambda k: k["published_at"])

        if regexpr is not None:
            prefix = "" if prefix is None else prefix
            pattern = re.compile(f"{prefix}{regexpr}")
            releases = [
                release
                for release in releases
                if pattern.match(release["name"]) is not None
            ]

        latest_release = releases[-1]["name"]

        if regexpr is not None:
            latest_release = re.search(regexpr, latest_release)
            self.chart_versions[chart]["latest"] = latest_release.group()
        else:
            self.chart_versions[chart]["latest"] = latest_release

    def _get_remote_versions(self):
        """
        Decipher where a list of chart versions is hosted and find the most recently
        published version
        """
        logger.info("Fetching most recently published helm chart versions...")
        for chart, info in self.inputs.chart_info.items():
            if (
                ("/gh-pages/" in info["url"])
                or info["url"].endswith("index.yaml")
                or info["url"].endswith("index.yml")
            ):
                self._pull_version_github_pages(
                    chart,
                    info["url"],
                    info.get("prefix", None),
                    info.get("regexpr", None),
                )
            elif ("github.com" in info["url"]) and ("/releases" in info["url"]):
                self._pull_version_github_releases(
                    chart,
                    info["url"],
                    info.get("prefix", None),
                    info.get("regexpr", None),
                )
            else:
                warnings.warn(
                    f"NotImplemented: Cannot currently retrieve version from URL type: {info['url']}"
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

        self.chart_versions = {
            chart["name"]: {"current": chart["version"]}
            for chart in self.inputs.chart_yaml["dependencies"]
            if chart["name"] in self.inputs.chart_info.keys()
        }

        self._get_remote_versions()
        self.inputs.charts_to_update = self._compare_chart_versions()
        self.inputs.chart_versions = self.chart_versions
