# Bump Helm Chart dependencies

This is an automatable bot that will check the chart dependencies of a Helm chart are up to date with their source.
If a new version is available, the bot will open a Pull Request to the host repository inserting the new chart dependency versions into the helm chart file.

[![CI tests](https://github.com/sgibson91/hub23-deploy-upgrades/actions/workflows/ci.yaml/badge.svg)](https://github.com/sgibson91/hub23-deploy-upgrades/actions/workflows/ci.yaml) ![coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/sgibson91/hub23-deploy-upgrades/main/badge_metadata.json) ![GitHub](https://img.shields.io/github/license/sgibson91/hub23-deploy-upgrades) [![badge](https://img.shields.io/static/v1?label=Code%20of&message=Conduct&color=blueviolet)](CODE_OF_CONDUCT.md) [![badge](https://img.shields.io/static/v1?label=Contributing&message=Guidelines&color=blueviolet)](CONTRIBUTING.md)

**Table of Contents:**

- [:mag: Overview](#mag-overview)
- [🤔 Assumptions `helm-bot` Makes](#-assumptions-helmbot-makes)
- [:pushpin: Installation and Requirements](#pushpin-installation-and-requirements)
- [:children_crossing: Usage](#children_crossing-usage)
  - [:lock: User Permissions](#lock-user-permissions)
  - [:clock2: CRON Expression](#clock2-cron-expression)
  - [:clapper: GitHub Action](#clapper-github-action)
- [:white_check_mark: Running Tests](#white_check_mark-running-tests)
- [:gift: Acknowledgements](#gift-acknowledgements)
- [:sparkles: Contributing](#sparkles-contributing)

---

## :mag: Overview

This is an overview of the steps the bot executes.

- Read the celm chart requirements file and find the versions of the dependencies
- Scrape the Helm chart source indexes and find the most recent version release for each dependency
- If there is a newer chart version available, then:
  - Create a new branch on the host repository
  - Add the new version(s) to the helm chart requirements file
  - Commit the file to the branch
  - Open a Pull Request to the default branch
  - Assign labels and reviewers to the Pull Request if required

A moderator should check and merge the Pull Request as appropriate.

## 🤔 Assumptions `helm-bot` Makes

Here is a list detailing the assumptions that the bot makes.

1. You have a GitHub Personal Access Token provided by the `ACCESS_TOKEN` environment variable
2. The configuration for your helm chart is in a pulic GitHub repository.

## :pushpin: Installation and Requirements

To install the bot, you will need to clone this repository and install the package.
It requires Python version >=3.7.

```bash
git clone https://github.com/sgibson91/hub23-deploy-upgrades.git
cd hub23-deploy-upgrades
python setup.py install
```

## :children_crossing: Usage

To run the bot, execute the following:

```bash
ACCESS_TOKEN="TOKEN" helm-bot [-h] [-t HEAD_BRANCH] [-b BASE_BRANCH] [-l LABELS [LABELS ...]] [-r REVIEWERS [REVIEWERS ...]] [--dry-run] repository chart_path chart_urls

Upgrade a local Helm Chart in a GitHub repository

positional arguments:
  repository            The GitHub repository where the Helm Chart is stored. In the form REPOSITORY_OWNER/REPOSITORY_NAME
  chart_path            The path the file that stores the helm chart dependencies
  chart_urls            A dictionary storing the location of the dependency charts and their versions

optional arguments:
  -h, --help            show this help message and exit
  -t HEAD_BRANCH, --head-branch HEAD_BRANCH
                        The git branch to commit to. Default: helm_dep_bump.
  -b BASE_BRANCH, --base-branch BASE_BRANCH
                        The base branch to open the Pull Request against. Default: main.
  -l LABELS [LABELS ...], --labels LABELS [LABELS ...]
                        List of labels to assign to the Pull Request
  -r REVIEWERS [REVIEWERS ...], --reviewers REVIEWERS [REVIEWERS ...]
                        List of GitHub users to request reviews for the Pull Request from
  --dry-run             Perform a dry-run helm upgrade
```

Where `TOKEN` is your GitHub PAT.

### :lock: User Permissions

#### GitHub API

When [creating the GitHub PAT](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token), it will need to be assigned the [`public_repo` scope](https://docs.github.com/en/developers/apps/scopes-for-oauth-apps#available-scopes).

### :clock2: CRON expression

To run this script at 10am daily, use the following cron expression:

```bash
0 10 * * * cd /path/to/hub23-deploy-upgrades && /path/to/python setup.py install && /path/to/helm-bot [--flags]
```

## :white_check_mark: Running Tests

After following the [installation instructions](#pushpin-installation-and-requirements), the test suite can be run as follows:

```bash
python -m pytest -vvv
```

`coverage.py` can also be used to generate a coverage report of the test suite:

```bash
python -m coverage run -m pytest -vvv
coverage report
```

An interactive HTML report can be generated with the command `coverage html` and accessed by opening `htmlcov/index.html` in your browser.

## :gift: Acknowledgements

Thank you to Christopher Hench ([@henchc](https://github.com/henchc)) who wrote and documented [`henchbot`](https://github.com/henchbot) which automatically opens Pull Requests to upgrade mybinder.org.
[Give his blog post a read!](https://hackmd.io/qC4ooA5TTn6xA2w-2OLHbA)

## :sparkles: Contributing

Thank you for wanting to contribute to the project! :tada:
Please read our [Code of Conduct](CODE_OF_CONDUCT.md) :purple_heart: and [Contributing Guidelines](CONTRIBUTING.md) :space_invader: to get you started.
