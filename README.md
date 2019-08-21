# HelmUpgradeBot for Hub23

This is a automatable bot that will check the Helm Chart version deployed on Hub23 against the published versions at [https://jupyterhub.github.io/helm-chart/#development-releases-binderhub](https://jupyterhub.github.io/helm-chart/#development-releases-binderhub).
If an upgrade is available, the bot will perform open a PR to the [hub23-deploy repo](https://github.com/alan-turing-institute/hub23-deploy) inserting the new BinderHub Helm Chart version into the Hub23 Helm Chart requirements file.

- [Overview](#overview)
- [Assumptions HelmUpgradeBot Makes](#assumptions-helmupgradebot-makes)
- [Requirements](#requirements)
- [Usage](#usage)
- [Permissions](#permissions)
- [Acknowledgements](#acknowledgements)

---

## Overview

This is an overview of the steps the bot executes.

* Read Hub23's Helm Chart requirements file and find the version of the BinderHub Helm Chart
* Scrape the BinderHub Helm Chart index and find the most recent version release
* If there is a newer chart version available, then:
  * Log into Azure and pull a Personal Access Token (PAT) from an Azure Key Vault
  * Fork and clone the `hub23-deploy` repo
  * Checkout a new branch
  * Add the new version to the hub23-chart requirements file
  * Stage, commit and push the file to the branch
  * Write and open a Pull Request to `alan-turing-institute/hub23-deploy`

A moderator should check and merge the PR and delete the branch as appropriate.

## Assumptions HelmUpgradeBot Makes

Here is a list detailing the assumptions that the bot makes.

1. A GitHub PAT is stored in an Azure Key Vault.
2. The configuration for your BinderHub deployment is in a pulic GitHub repo.
3. Your deployment repo contains a local Helm Chart with a `requirements.yaml` file.

## Requirements

The bot requires Python v3.7 and the `pandas` and `pyyaml` packages listed in [`requirements.txt`](./requirements.txt), which can be installed using `pip`:

```
pip install -r requirements.txt
```

It will require the following command line interface:

* [Microsoft Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest)

### Install Azure CLI

```
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### Install `kubectl`

```
curl -LO https://storage.googleapis.com/kubernetes-release/release/`curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt`/bin/linux/amd64/kubectl
curl -LO https://storage.googleapis.com/kubernetes-release/release/v1.15.0/bin/linux/amd64/kubectl
chmod +x ./kubectl
sudo mv ./kubectl /usr/local/bin/kubectl
```

### Install `helm`

```
curl -LO https://git.io/get_helm.sh
chmod 700 get_helm.sh
./get_helm.sh
```

## Usage

To run the bot, simply execute the following:

```
python HelmUpgradeBot.py \
    --repo-owner [-o] REPO-OWNER \
    --repo-name [-n] REPO-NAME \
    --branch [-b] BRANCH \
    --deployment [-d] BINDERHUB-NAME \
    --token-name [-t] TOKEN-NAME \
    --keyvault [-v] KEYVAULT \
    --chart-name [-c] CHART-NAME \
    --identity \
    --dry-run
```
where:
* `REPO-OWNER` is the owner of the deployment repo;
* `REPO-NAME` is the name of the deployment repo;
* `BRANCH` is the git branch name to commit changes to;
* `BINDERHUB-NAME` is the name your BinderHub is deployed under;
* `TOKEN-NAME` is the name of the secret containing the PAT in the Azure Key Vault;
* `KEYVAULT` is the name of the Azure Key Vault;
* `CHART-NAME` is the name of the local Helm Chart;
* `--identity` enables logging into Azure with a [Managed System Identity](https://docs.microsoft.com/en-gb/azure/active-directory/managed-identities-azure-resources/overview); and
* `--dry-run` performs a dry-run of the upgrade and does not open a Pull Request.

## Permissions

The user (or machine) running this script will need _at least_:

* `Contributor` role permissions to the Kubernetes cluster to be upgraded
* Permission to get secrets from the Azure Key Vault

## CRON expression

To run this script at 10am daily:

```
0 10 * * * cd /path/to/hub23-deploy-upgrades && ~/path/to/python HelmUpgradeBot.py [--flags]
```

## Acknowledgements

Thank you to Christopher Hench ([@henchc](https://github.com/henchc)) who wrote and documented [`henchbot`](https://github.com/henchbot) which automatically opens PRs to upgrade mybinder.org.
[Give his blog post a read!](https://hackmd.io/qC4ooA5TTn6xA2w-2OLHbA)
