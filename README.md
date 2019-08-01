# HelmUpgradeBot for Hub23

This is a automatable bot that will check the Helm Chart version deployed on Hub23 against the published versions at [https://jupyterhub.github.io/helm-chart/#development-releases-binderhub](https://jupyterhub.github.io/helm-chart/#development-releases-binderhub).
If an upgrade is available, the bot will perform the upgrade and open a PR to the [hub23-deploy repo](https://github.com/alan-turing-institute/hub23-deploy) documenting the upgrade in the changelog.

- [Overview](#overview)
- [Assumptions HelmUpgradeBot Makes](#assumptions-helmupgradebot-makes)
- [Requirements](#requirements)
- [Usage](#usage)
- [Acknowledgements](#acknowledgements)

---

## Overview

This is an overview of the steps the bot executes.

* Pulls a Personal Access Token (PAT) from an Azure keyvault
* Read Hub23's changelog file and find date and version of the last helm chart upgrade
* Scrape the BinderHub Helm Chart index and find the most recent version release
* If there is a newer chart version available, then:
  * Fork and clone the `hub23-deploy` repo
  * Generate the config files by running `generate-configs.py`
  * Perform the upgrade by running `upgrade.py` with the new version number as an argument
  * Checkout a new branch
  * Add the new version to the changelog
  * Stage, commit and push the changelog to the branch
  * Write and open a Pull Request to `alan-turing-institute/hub23-deploy`

A moderator should check and merge the PR and delete the branch as appropriate.

## Assumptions HelmUpgradeBot Makes

Here is a list detailing the assumptions that the bot makes.

1. A GitHub PAT is stored in an Azure Key Vault.
2. The configuration for your BinderHub deployment is in a pulic GitHub repo.
3. Your deployment repo contains scripts to generate the configuration files (for example, `make-config-files.sh`) and to perform the helm upgrade (for example, `upgrade.sh`) which takes the new version as a command line argument. See the `hub23-deploy` repo for how these scripts may be set out.
4. Your deployment repo contains a changelog file (for example, `changelog.txt`) of the form `date of upgrade: deployed version`.

## Requirements

The bot requires Python v3.7 and the `pandas` and `pyyaml` packages listed in [`requirements.txt`](./requirements.txt), which can be installed using `pip`:

```
pip install -r requirements.txt
```

When the bot tries to run `generate-configs.py` and `upgrade.py` from the `hub23-deploy` repo, it will require the following three command line interfaces:

* [Microsoft Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest)
* [Kubernetes (`kubectl`)](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
* [Helm](https://helm.sh/docs/using_helm/#installing-helm)

## Usage

To run the bot, simply execute the following:

```
python HelmUpgradeBot.py \
    --repo-owner [-o] REPO-OWNER \
    --repo-name [-n] REPO-NAME \
    --branch [-b] BRANCH \
    --files [-f] FILE1 FILE2 ... \
    --deployment [-d] BINDERHUB-NAME \
    --token-name [-t] TOKEN-NAME \
    --keyvault [-v] KEYVAULT \
    --identity \
    --dry-run
```
where:
* `REPO-OWNER` is the owner of the deployment repo;
* `REPO-NAME` is the name of the deployment repo;
* `BRANCH` is the git branch name to commit changes to;
* `FILE1` is the name of the changelog file;
* `BINDERHUB-NAME` is the name your BinderHub is deployed under;
* `TOKEN-NAME` is the name of the secret containing the PAT in the Azure Key Vault;
* `KEYVAULT` is the name of the Azure Key Vault;
* `--identity` enables logging into Azure with a [Managed System Identity](https://docs.microsoft.com/en-gb/azure/active-directory/managed-identities-azure-resources/overview); and
* `--dry-run` performs a dry-run of the upgrade and does not open a Pull Request.

Multiple filenames can be parsed to `--files` though the script will need to be told how to update them.

## Acknowledgements

Thank you to Christopher Hench ([@henchc](https://github.com/henchc)) who wrote and documented [`henchbot`](https://github.com/henchbot) which automatically opens PRs to upgrade mybinder.org.
[Give his blog post a read!](https://hackmd.io/qC4ooA5TTn6xA2w-2OLHbA)
