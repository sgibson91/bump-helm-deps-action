# HelmUpgradeBot for Hub23

This is a automatable bot that will check the Helm Chart version deployed on Hub23 against the published versions at [https://jupyterhub.github.io/helm-chart/#development-releases-binderhub](https://jupyterhub.github.io/helm-chart/#development-releases-binderhub).
If an upgrade is available, the bot will perform the upgrade and open a PR to the [hub23-deploy repo](https://github.com/alan-turing-institute/hub23-deploy) documenting the upgrade in the changelog.

## Overview

* Read Hub23's changelog file and find date and version of the last helm chart upgrade
* Scrape the BinderHub Helm Chart index and find the most recent version release
* If there is a newer chart version available, then:
  * Fork and clone the hub23-deploy repo
  * Generate the config files by running `make-config-files.sh`
  * Perform the upgrade by running `upgrade.sh` with the new version number of an argument
  * Checkout a new branch
  * Add the new version to the changelog
  * Stage, commit and push the changelog to the branch
  * Write and open a Pull Request to `alan-turing-institute/hub23-deploy`

A moderator should check and merge the PR and delete the branch as appropriate.

## Usage

To run the bot, simply execute the following parsing a GitHub access token as an environment variable:

```
BOT_TOKEN="<Personal Access Token for HelmUpgradeBot>" python HelmUpgradeBot.py
```

## Requirements

The bot requires Python v3.7 and the `pandas` and `pyyaml` packages listed in [`requirements.txt`](./requirements.txt), which can be installed using `pip`:

```
pip install -r requirements.txt
```

When the bot tries to run `make-config-files.sh` and `upgrade.sh` from the `hub23-deploy` repo, it will require the following three command line interfaces:

* [Microsoft Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest)
* [Kubernetes (`kubectl`)](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
* [Helm](https://helm.sh/docs/using_helm/#installing-helm)

## Acknowledgements

Thank you to Christopher Hench ([@henchc](https://github.com/henchc)) who wrote and documented [`henchbot`](https://github.com/henchbot) which automatically opens PRs to upgrade mybinder.org.
[Give his blog post a read!](https://hackmd.io/qC4ooA5TTn6xA2w-2OLHbA)
