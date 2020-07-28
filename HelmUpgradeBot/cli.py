import os
import sys
import argparse
from .app import run


def parse_args(args):
    # Create argument parser
    DESCRIPTION = "Upgrade the Helm Chart of the Hub23 Helm Chart in the hub23-deploy GitHub repository"
    parser = argparse.ArgumentParser(description=DESCRIPTION)

    # Define positional arguments
    parser.add_argument(
        "repo_owner", type=str, help="The GitHub repository owner"
    )
    parser.add_argument("repo_name", type=str, help="The deployment repo name")
    parser.add_argument(
        "chart_name", type=str, help="The name of the local helm chart"
    )

    # Define optional arguments that take parameters
    parser.add_argument(
        "-k",
        "--keyvault",
        type=str,
        help="Name of the Azure Key Vault storing secrets for the BinderHub",
    )
    parser.add_argument(
        "-n",
        "--token-name",
        type=str,
        help="Name of the bot's access token as stored in the Azure Key Vault",
    )
    parser.add_argument(
        "-t",
        "--target-branch",
        type=str,
        default="helm_chart_bump",
        help="The git branch to commit to. Default: helm_chart_bump.",
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
        default=None,
        help="List of labels to assign to the Pull Request",
    )

    # Define optional boolean flags
    parser.add_argument(
        "--identity",
        action="store_true",
        help="Login to Azure using a Managed System Identity",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Perform a dry-run helm upgrade"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print output to the console. Default is to write to a log file.",
    )

    return parser.parse_args()


def check_parser(args):
    keyvault_cond = args.keyvault is None
    token_cond = args.token_name is None

    if (keyvault_cond and not token_cond) or (
        token_cond and not keyvault_cond
    ):
        raise ValueError(
            "Both --keyvault [-k] and --token-name [-n] flags must be set"
        )
    elif keyvault_cond and token_cond:
        # Check environment variables
        api_token = os.environ.get("API_TOKEN")

        if api_token is None:
            raise ValueError(
                "An API token must be provided. This can be done either with the API_TOKEN environment variable, or by providing keyvault and token names via the --keyvault [-k] and --token-name [-n] flags respectively."
            )
        else:
            setattr(args, "token", api_token)
    else:
        setattr(args, "token", None)


def main():
    """Main Function"""
    args = parse_args(sys.argv[1:])
    check_parser(args)

    run(
        chart_name=args.chart_name,
        repo_owner=args.repo_owner,
        repo_name=args.repo_name,
        base_branch=args.base_branch,
        target_branch=args.target_branch,
        labels=args.labels,
        token=args.token,
        token_name=args.token_name,
        keyvault=args.keyvault,
        dry_run=args.dry_run,
        identity=args.identity,
    )


if __name__ == "__main__":
    main()
