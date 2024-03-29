import base64
import json
import os

from loguru import logger

from .github_api import GitHubAPI
from .pull_version_info import HelmChartVersionPuller
from .yaml_parser import YamlParser

yaml = YamlParser()


class UpdateHelmDeps:
    """Update the versions of helm subcharts of a local helm chart"""

    def __init__(
        self,
        repository,
        github_token,
        chart_path,
        chart_urls,
        base_branch="main",
        head_branch="bump-helm-deps",
        labels=[],
        reviewers=[],
        team_reviewers=[],
        dry_run=False,
    ):
        self.repository = repository
        self.chart_path = chart_path
        self.chart_urls = chart_urls
        self.base_branch = base_branch
        self.labels = labels
        self.reviewers = reviewers
        self.team_reviewers = team_reviewers
        self.dry_run = dry_run

        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {github_token}",
        }
        self.chart_name = self.chart_path.split("/")[-2]
        self.head_branch = "/".join([head_branch, self.chart_name])

    def update_versions(self):
        """Update the dependencies of a local helm chart with the latest versions

        Returns:
            chart_yaml (str): The updated helm chart dependencies in YAML format and
                encoded in base64
        """
        for chart in self.charts_to_update:
            indx = next(
                (
                    indx
                    for (indx, chart_dep) in enumerate(self.chart_yaml["dependencies"])
                    if chart_dep["name"] == chart
                ),
                None,
            )
            self.chart_yaml["dependencies"][indx]["version"] = self.chart_versions[
                chart
            ]["latest"]

        encoded_chart_yaml = yaml.object_to_yaml_str(self.chart_yaml).encode("utf-8")
        base64_bytes = base64.b64encode(encoded_chart_yaml)
        chart_yaml = base64_bytes.decode("utf-8")

        return chart_yaml

    def update(self):
        """Run the action to check the helm chart dependencies are up to date"""
        github = GitHubAPI(self)
        github.find_existing_pull_request()

        if github.pr_exists:
            version_puller = HelmChartVersionPuller(self, self.head_branch)
        else:
            version_puller = HelmChartVersionPuller(self, self.base_branch)

        version_puller.get_chart_versions()

        if len(self.charts_to_update) > 0 and not self.dry_run:
            logger.info(
                "The following subcharts can be updated: {}", self.charts_to_update
            )

            if not github.pr_exists:
                resp = github.get_ref(self.base_branch)
                github.create_ref(self.head_branch, resp["object"]["sha"])

            updated_chart_yaml = self.update_versions()
            commit_msg = f"Bump charts {[chart for chart in self.charts_to_update]} to versions {[self.chart_versions[chart]['latest'] for chart in self.charts_to_update]}, respectively"
            github.create_commit(commit_msg, updated_chart_yaml)
            github.create_update_pull_request()

        elif len(self.charts_to_update) > 0 and self.dry_run:
            logger.info(
                "The following subcharts can be updated: {}: A Pull Request will not be opened due to the --dry-run flag being set.",
                self.charts_to_update,
            )
        else:
            logger.info("All subcharts are up-to-date!")


def split_str_to_list(input_str, split_char=","):
    """Split a string into a list of elements.

    Args:
        input_str (str): The string to split
        split_char (str, optional): The character to split the string by. Defaults
            to ",".

    Returns:
        (list): The string split into a list
    """
    # Split a string into a list using `,` char
    split_str = input_str.split(split_char)

    # For each element in split_str, strip leading/trailing whitespace
    for i, element in enumerate(split_str):
        split_str[i] = element.strip()

    return split_str


def main():
    # Retrieve environment variables
    chart_path = os.environ.get("INPUT_CHART_PATH", None)
    chart_urls = json.loads(os.environ.get("INPUT_CHART_URLS", "null"))
    github_token = os.environ.get("INPUT_GITHUB_TOKEN", None)
    repository = os.environ.get("INPUT_REPOSITORY", None)
    base_branch = os.environ.get("INPUT_BASE_BRANCH", None)
    head_branch = os.environ.get("INPUT_HEAD_BRANCH", None)
    labels = os.environ.get("INPUT_LABELS", [])
    reviewers = os.environ.get("INPUT_REVIEWERS", [])
    team_reviewers = os.environ.get("INPUT_TEAM_REVIEWERS", [])
    dry_run = os.environ.get("INPUT_DRY_RUN", False)

    # Reference dict for required inputs
    required_vars = {
        "CHART_PATH": chart_path,
        "CHART_URLS": chart_urls,
        "GITHUB_TOKEN": github_token,
        "REPOSITORY": repository,
        "BASE_BRANCH": base_branch,
        "HEAD_BRANCH": head_branch,
    }

    # Check all required inputs are properly set
    for k, v in required_vars.items():
        if v is None:
            raise ValueError(f"{k} must be set!")

    # If labels/reviewers/team_reviewers have been provided, transform from string into list
    if labels:
        labels = split_str_to_list(labels)
    if reviewers:
        reviewers = split_str_to_list(reviewers)
    if team_reviewers:
        team_reviewers = split_str_to_list(team_reviewers)

    # Check the dry_run variable is properly set
    if isinstance(dry_run, str) and (dry_run == "true"):
        dry_run = True
    elif isinstance(dry_run, str) and (dry_run == "false"):
        dry_run = False
    elif isinstance(dry_run, bool):
        # Pass silently since input is a boolean as expected
        pass
    else:
        # If none of the above conditions pass then raise an error
        raise ValueError(
            "DRY_RUN variable can only take values 'true' or 'false' (either str or bool type). "
            + f"You have provided: {dry_run} ({type(dry_run)})"
        )

    update_helm_deps = UpdateHelmDeps(
        repository,
        github_token,
        chart_path,
        chart_urls,
        base_branch=base_branch,
        head_branch=head_branch,
        labels=labels,
        reviewers=reviewers,
        team_reviewers=team_reviewers,
        dry_run=dry_run,
    )
    update_helm_deps.update()


if __name__ == "__main__":
    main()
