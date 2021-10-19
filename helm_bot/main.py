import json
import os
from typing import List

from .app import run

API_ROOT = "https://api.github.com"


def split_str_to_list(input_str: str) -> List[str]:
    # Split a string into a list using `,` char
    split_str = input_str.split(",")

    # For each element in split_str, strip leading/trailing whitespace
    for i, element in enumerate(split_str):
        split_str[i] = element.strip()

    return split_str


def main():
    # Retrieve environment variables
    chart_path = (
        os.environ["INPUT_CHART_PATH"] if "INPUT_CHART_PATH" in os.environ else None
    )
    chart_urls = (
        json.loads(os.environ["INPUT_CHART_URLS"])
        if "INPUT_CHART_URLS" in os.environ
        else None
    )
    github_token = (
        os.environ["INPUT_GITHUB_TOKEN"] if "INPUT_GITHUB_TOKEN" in os.environ else None
    )
    repository = (
        os.environ["INPUT_REPOSITORY"] if "INPUT_REPOSITORY" in os.environ else None
    )
    base_branch = (
        os.environ["INPUT_BASE_BRANCH"] if "INPUT_BASE_BRANCH" in os.environ else None
    )
    head_branch = (
        os.environ["INPUT_HEAD_BRANCH"] if "INPUT_HEAD_BRANCH" in os.environ else None
    )
    labels = os.environ["INPUT_LABELS"] if "INPUT_LABELS" in os.environ else []
    reviewers = os.environ["INPUT_REVIEWERS"] if "INPUT_REVIEWERS" in os.environ else []
    dry_run = os.environ["INPUT_DRY_RUN"] if "INPUT_DRY_RUN" in os.environ else False

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

    # If labels/reviewers have been provided, transform from string into list
    if isinstance(labels, str) and (len(labels) > 0):
        labels = split_str_to_list(labels)
    if isinstance(reviewers, str) and (len(reviewers) > 0):
        reviewers = split_str_to_list(reviewers)

    # Check the dry_run variable is properly set
    if isinstance(dry_run, str) and (dry_run == "true"):
        dry_run = True
    elif isinstance(dry_run, str) and (dry_run != "true"):
        dry_run = False
    elif isinstance(dry_run, bool) and not dry_run:
        pass
    else:
        raise ValueError("DRY_RUN variable can only take values 'true' or 'false'")

    # Set API URL
    repo_api = "/".join([API_ROOT, "repos", repository])

    # Create a header for API requests
    header = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {github_token}",
    }

    run(
        repo_api,
        header,
        chart_path,
        chart_urls,
        base_branch,
        head_branch,
        labels=labels,
        reviewers=reviewers,
        dry_run=dry_run,
    )


if __name__ == "__main__":
    main()
