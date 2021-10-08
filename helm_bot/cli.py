import argparse
import json
import os
import sys

from .app import run

API_ROOT = "https://api.github.com"


def parse_args(args):
    # Create argument parser
    DESCRIPTION = "Upgrade a local Helm Chart in a GitHub repository"
    parser = argparse.ArgumentParser(description=DESCRIPTION)

    # Define positional arguments
    parser.add_argument(
        "repository",
        type=str,
        help="The GitHub repository where the Helm Chart is stored. In the form REPOSITORY_OWNER/REPOSITORY_NAME",
    )
    parser.add_argument(
        "chart_path",
        type=str,
        help="The path the file that stores the helm chart dependencies",
    )
    parser.add_argument(
        "chart_urls",
        type=json.loads,
        help="A dictionary storing the location of the dependency charts and their versions",
    )

    # Define optional arguments that take parameters
    parser.add_argument(
        "-t",
        "--head-branch",
        type=str,
        default="helm_dep_bump",
        help="The git branch to commit to. Default: helm_dep_bump.",
    )
    parser.add_argument(
        "-b",
        "--base-branch",
        type=str,
        default="main",
        help="The base branch to open the Pull Request against. Default: main.",
    )
    parser.add_argument(
        "-l",
        "--labels",
        nargs="+",
        default=[],
        help="List of labels to assign to the Pull Request",
    )
    parser.add_argument(
        "-r",
        "--reviewers",
        nargs="+",
        default=[],
        help="List of GitHub users to request reviews for the Pull Request from",
    )

    # Define optional boolean flags
    parser.add_argument(
        "--dry-run", action="store_true", help="Perform a dry-run helm upgrade"
    )

    return parser.parse_args()


def check_parser(args):
    # Check environment variables
    access_token = os.environ.get("ACCESS_TOKEN")

    if access_token is None:
        raise ValueError(
            "A GitHub access token must be provided. This can be done with the ACCESS_TOKEN environment variable."
        )
    else:
        setattr(args, "token", access_token)


def main():
    """Main Function"""
    args = parse_args(sys.argv[1:])
    check_parser(args)

    repo_api = "/".join([API_ROOT, "repos", args.repository])
    header = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {args.token}",
    }

    run(
        api_url=repo_api,
        header=header,
        chart_path=args.chart_path,
        chart_urls=args.chart_urls,
        base_branch=args.base_branch,
        head_branch=args.head_branch,
        labels=args.labels,
        reviewers=args.reviewers,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
