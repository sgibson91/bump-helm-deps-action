# HelmUpgradeBot for Hub23

This is a automatable bot that will check the chart dependencies of the Hub23 Helm Chart are up to date with their source.
If an upgrade is available, the bot will open a PR to the [`alan-turing-institute/hub23-deploy` repo](https://github.com/alan-turing-institute/hub23-deploy) inserting the new chart dependency versions into the Hub23 Helm Chart requirements file.

- [Overview](#overview)
- [Assumptions HelmUpgradeBot Makes](#assumptions-helmupgradebot-makes)
- [Requirements](#requirements)
  - [Install Azure CLI](#install-azure-cli)
- [Usage](#usage)
  - [Permissions](#permissions)
  - [CRON Expression](#cron-expression)
- [Pre-commit Hook](#pre-commit-hook)
- [Acknowledgements](#acknowledgements)

---

## Overview

This is an overview of the steps the bot executes.

- Log into Azure and pull a Personal Access Token (PAT) from an Azure Key Vault
- Read Hub23's Helm Chart requirements file and find the versions of the dependencies
- Scrape the Helm Chart source indexes and find the most recent version release for each dependency
- If there is a newer chart version available, then:
  - Fork and clone the [`alan-turing-institute/hub23-deploy`](https://github.com/alan-turing-institute/hub23-deploy) repo
  - Checkout a new branch
  - Add the new version(s) to the hub23-chart requirements file
  - Stage, commit and push the file to the branch
  - Open a Pull Request to the parent repo
  - Assign labels to the Pull Request if required.

A moderator should check and merge the PR as appropriate.

## Assumptions HelmUpgradeBot Makes

Here is a list detailing the assumptions that the bot makes.

1. A GitHub PAT is stored in an Azure Key Vault.
2. The configuration for your BinderHub deployment is in a pulic GitHub repo.
3. Your deployment repo contains a local Helm Chart with a `requirements.yaml` file.

## Installation and Requirements

To install the bot, you will need to clone this repo and install the package.
It requires Python version >=3.7.

```bash
git clone https://github.com/HelmUpgradeBot/hub23-deploy-upgrades.git
cd hub23-deploy-upgrades
python setup.py install
```

You will also need to install the following command line interface:

- [Microsoft Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest)

### Install Azure CLI

```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

## Usage

To run the bot, simply execute the following:

```bash
HelmUpgradeBot REPO-OWNER REPO-NAME BINDERHUB-NAME \
    CHART-NAME KEYVAULT TOKEN-NAME \
    --branch [-b] BRANCH \
    --labels [-l] LABELS \
    --identity \
    --dry-run
```

where:

- `REPO-OWNER` is the owner of the deployment repo;
- `REPO-NAME` is the name of the deployment repo;
- `BRANCH` is the git branch name to commit changes to;
- `LABELS` are the labels to be assigned to the Pull Request (can accept multiple values);
- `BINDERHUB-NAME` is the name your BinderHub is deployed under;
- `CHART-NAME` is the name of the local Helm Chart;
- `KEYVAULT` is the name of the Azure Key Vault;
- `TOKEN-NAME` is the name of the secret containing the PAT in the Azure Key Vault;
- `BRANCH` is the git branch name to commit changes to;
- `--identity` enables logging into Azure with a [Managed System Identity](https://docs.microsoft.com/en-gb/azure/active-directory/managed-identities-azure-resources/overview); and
- `--dry-run` performs a dry-run of the upgrade and does not open a Pull Request.

### Permissions

The user (or machine) running this script will need _at least_:

- `Contributor` role permissions to the Kubernetes cluster to be upgraded, and
- Permission to get secrets from the Azure Key Vault (`Get` and `List`).

### CRON expression

To run this script at 10am daily, use the following cron expression:

```bash
0 10 * * * cd /path/to/hub23-deploy-upgrades && ~/path/to/python setup.py install && HelmUpgradeBot [--flags]
```

## Pre-commit Hook

For developing this bot, there is a pre-commit hook that will format the Python code using [black](https://github.com/psf/black) and [flake8](http://flake8.pycqa.org/en/latest/).
To install the hook, do the following:

```bash
pip install -r requirements-dev.txt
pre-commit install
```

## Acknowledgements

Thank you to Christopher Hench ([@henchc](https://github.com/henchc)) who wrote and documented [`henchbot`](https://github.com/henchbot) which automatically opens PRs to upgrade mybinder.org.
[Give his blog post a read!](https://hackmd.io/qC4ooA5TTn6xA2w-2OLHbA)
