# HelmUpgradeBot for Hub23

This is an automatable bot that will check the chart dependencies of the Hub23 Helm chart are up to date with their source.
If a new version is available, the bot will open a Pull Request to the [`alan-turing-institute/hub23-deploy` repository](https://github.com/alan-turing-institute/hub23-deploy) inserting the new chart dependency versions into the Hub23 Helm Chart requirements file.

**Table of Contents:**

- [:mag: Overview](#mag-overview)
- [🤔 Assumptions HelmUpgradeBot Makes](#-assumptions-helmupgradebot-makes)
- [:pushpin: Requirements](#pushpin-installation-and-requirements)
  - [:cloud: Install Azure CLI](#cloud-install-azure-cli)
- [:children_crossing: Usage](#children_crossing-usage)
  - [:lock: Permissions](#lock-permissions)
  - [:clock2: CRON Expression](#clock2-cron-expression)
- [:leftwards_arrow_with_hook: Pre-commit Hook](#leftwards_arrow_with_hook-pre-commit-hook)
- [:gift: Acknowledgements](#gift-acknowledgements)

---

## :mag: Overview

This is an overview of the steps the bot executes.

- Log into Azure and pull a GitHub Personal Access Token (PAT) from an Azure Key Vault
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

1. A GitHub PAT is stored in an Azure Key Vault.
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
HelmUpgradeBot REPO-OWNER REPO-NAME BINDERHUB-NAME \
    CHART-NAME KEYVAULT TOKEN-NAME \
    --branch [-b] BRANCH \
    --labels [-l] LABELS \
    --identity \
    --dry-run
```

where:

- `REPO-OWNER` is the owner of the deployment repository;
- `REPO-NAME` is the name of the deployment repository;
- `BRANCH` is the git branch name to commit changes to;
- `LABELS` are the labels to be assigned to the Pull Request (can accept multiple values);
- `BINDERHUB-NAME` is the name your BinderHub is deployed under;
- `CHART-NAME` is the name of the local Helm chart;
- `KEYVAULT` is the name of the Azure Key Vault;
- `TOKEN-NAME` is the name of the secret containing the GitHub PAT in the Azure Key Vault;
- `BRANCH` is the git branch name to commit changes to;
- `--identity` enables logging into Azure with a [Managed System Identity](https://docs.microsoft.com/en-gb/azure/active-directory/managed-identities-azure-resources/overview); and
- `--dry-run` performs a dry-run of the upgrade and does not open a Pull Request.

### :lock: Permissions

The user (or machine) running this script will need _at least_:

- `Contributor` role permissions to the Kubernetes cluster to be upgraded, and
- Permission to get secrets from the Azure Key Vault (`Get` and `List`).

### :clock2: CRON expression

To run this script at 10am daily, use the following cron expression:

```bash
0 10 * * * cd /path/to/hub23-deploy-upgrades && /path/to/python setup.py install && /path/to/HelmUpgradeBot [--flags]
```

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
