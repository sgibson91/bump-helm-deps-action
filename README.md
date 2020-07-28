# HelmUpgradeBot for Hub23

This is an automatable bot that will check the chart dependencies of the Hub23 Helm chart are up to date with their source.
If a new version is available, the bot will open a Pull Request to the [`alan-turing-institute/hub23-deploy` repository](https://github.com/alan-turing-institute/hub23-deploy) inserting the new chart dependency versions into the Hub23 Helm Chart requirements file.

![GitHub](https://img.shields.io/github/license/HelmUpgradeBot/hub23-deploy-upgrades) [![badge](https://img.shields.io/static/v1?label=Code%20of&message=Conduct&color=blueviolet)](CODE_OF_CONDUCT.md) [![badge](https://img.shields.io/static/v1?label=Contributing&message=Guidelines&color=blueviolet)](CONTRIBUTING.md) [![GitHub labels](https://img.shields.io/github/labels/HelmUpgradeBot/hub23-deploy-upgrades/good%20first%20issue)](https://github.com/HelmUpgradeBot/hub23-deploy-upgrades/labels/good%20first%20issue) [![GitHub labels](https://img.shields.io/github/labels/HelmUpgradeBot/hub23-deploy-upgrades/help%20wanted)](https://github.com/HelmUpgradeBot/hub23-deploy-upgrades/labels/help%20wanted)

**Table of Contents:**

- [:mag: Overview](#mag-overview)
- [🤔 Assumptions HelmUpgradeBot Makes](#-assumptions-helmupgradebot-makes)
- [:pushpin: Requirements](#pushpin-installation-and-requirements)
  - [:cloud: Install Azure CLI](#cloud-install-azure-cli)
- [:children_crossing: Usage](#children_crossing-usage)
  - [:lock: User Permissions](#lock-user-permissions)
  - [:clock2: CRON Expression](#clock2-cron-expression)
  - [:clapper: GitHub Action](#clapper-github-action)
- [:leftwards_arrow_with_hook: Pre-commit Hook](#leftwards_arrow_with_hook-pre-commit-hook)
- [:gift: Acknowledgements](#gift-acknowledgements)
- [:sparkles: Contributing](#sparkles-contributing)

---

## :mag: Overview

This is an overview of the steps the bot executes.

- If a GitHub Personal Access Token (PAT) is not provided as an environment variable, log into Azure and pull one from an Azure Key Vault
  - The login will either be interactively if run locally or via a [Managed System Identity](https://docs.microsoft.com/en-gb/azure/active-directory/managed-identities-azure-resources/overview) if run from a server.
    The server will require [`GET` permissions to the secrets](https://docs.microsoft.com/en-us/azure/key-vault/secrets/about-secrets#secret-access-control) stored in the Azure Key Vault.
- Read Hub23's Helm chart requirements file and find the versions of the dependencies
- Scrape the Helm chart source indexes and find the most recent version release for each dependency
- If there is a newer chart version available, then:
  - Fork and clone the [`alan-turing-institute/hub23-deploy`](https://github.com/alan-turing-institute/hub23-deploy) repository
  - Checkout a new branch
  - Add the new version(s) to the hub23-chart requirements file
  - Stage, commit and push the file to the branch
  - Open a Pull Request to the parent repository
  - Assign labels to the Pull Request if required

A moderator should check and merge the Pull Request as appropriate.

## 🤔 Assumptions HelmUpgradeBot Makes

Here is a list detailing the assumptions that the bot makes.

1. You have a GitHub PAT
   1. It is stored in an Azure Key Vault or provided by the `API_TOKEN` environment variable
2. The configuration for your BinderHub deployment is in a pulic GitHub repository.
3. Your deployment repository contains a local Helm chart with a `requirements.yaml` file.

## :pushpin: Installation and Requirements

To install the bot, you will need to clone this repository and install the package.
It requires Python version >=3.7.

```bash
git clone https://github.com/HelmUpgradeBot/hub23-deploy-upgrades.git
cd hub23-deploy-upgrades
python setup.py install
```

You will also need to install the [Microsoft Azure command line interface](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest).

### :cloud: Install the Azure CLI

To install the Azure command line interface, run the following:

```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

## :children_crossing: Usage

To run the bot, execute the following:

```bash
usage: helm-bot [-h] [-k KEYVAULT] [-n TOKEN_NAME] [-t TARGET_BRANCH]
                [-b BASE_BRANCH] [-l LABELS [LABELS ...]] [--identity]
                [--dry-run] [-v]
                repo_owner repo_name chart_name

Upgrade the Helm Chart of the Hub23 Helm Chart in the hub23-deploy GitHub
repository

positional arguments:
  repo_owner            The GitHub repository owner
  repo_name             The deployment repo name
  chart_name            The name of the local helm chart

optional arguments:
  -h, --help            show this help message and exit
  -k KEYVAULT, --keyvault KEYVAULT
                        Name of the Azure Key Vault storing secrets for the
                        BinderHub
  -n TOKEN_NAME, --token-name TOKEN_NAME
                        Name of the bot's access token as stored in the Azure
                        Key Vault
  -t TARGET_BRANCH, --target-branch TARGET_BRANCH
                        The git branch to commit to. Default: helm_chart_bump.
  -b BASE_BRANCH, --base-branch BASE_BRANCH
                        The base branch to open the Pull Request against.
                        Default: main.
  -l LABELS [LABELS ...], --labels LABELS [LABELS ...]
                        List of labels to assign to the Pull Request
  --identity            Login to Azure using a Managed System Identity
  --dry-run             Perform a dry-run helm upgrade
  -v, --verbose         Print output to the console. Default is to write to a
                        log file.
```

Alternatively, the GitHub PAT can be provided directly using the `API_TOKEN` environment variable, like so:

```bash
API_TOKEN="your-token-here" HelmUpgradeBot repo_owner repo_name deployment chart_name [--flags]
```

### :lock: User Permissions

The user (or machine) running this script will need _at least_:

- `Contributor` role permissions to the Kubernetes cluster to be upgraded, and
- Permission to get secrets from the Azure Key Vault (`Get` and `List`).

### :clock2: CRON expression

To run this script at 10am daily, use the following cron expression:

```bash
0 10 * * * cd /path/to/hub23-deploy-upgrades && /path/to/python setup.py install && /path/to/HelmUpgradeBot [--flags]
```

### :clapper: GitHub Action

Rather than pay for a Virtual Machine to run the bot, it could be run in a [GitHub Action workflow](.github/workflows/run-bot.yml) instead.
The default secret `GITHUB_TOKEN` should have enough permissions for everything provided all repositories are public.

## :leftwards_arrow_with_hook: Pre-commit Hook

For developing this bot, there is a pre-commit hook that will format the Python code using [black](https://github.com/psf/black) and [flake8](http://flake8.pycqa.org/en/latest/).
To install the hook, run the following:

```bash
pip install -r dev-requirements.txt
pre-commit install
```

## :gift: Acknowledgements

Thank you to Christopher Hench ([@henchc](https://github.com/henchc)) who wrote and documented [`henchbot`](https://github.com/henchbot) which automatically opens Pull Requests to upgrade mybinder.org.
[Give his blog post a read!](https://hackmd.io/qC4ooA5TTn6xA2w-2OLHbA)

## :sparkles: Contributing

Thank you for wanting to contribute to the project! :tada:
Please read our [Code of Conduct](CODE_OF_CONDUCT.md) :purple_heart: and [Contributing Guidelines](CONTRIBUTING.md) :space_invader: to get you started.
