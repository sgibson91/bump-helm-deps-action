<center>

<img src="helm-bot-logo.png" alt="Helm Bot logo" width="100">

<h1>Bump Helm Chart Dependencies</h1>

This is an GitHub Action that will check the chart dependencies of a Helm chart are up to date with their source.
If a new version is available, the Action will open a Pull Request inserting the new chart dependency versions into the helm chart file.

[![CI tests](https://github.com/sgibson91/bump-helm-deps-action/actions/workflows/ci.yaml/badge.svg)](https://github.com/sgibson91/bump-helm-deps-action/actions/workflows/ci.yaml) ![coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/sgibson91/bump-helm-deps-action/main/badge_metadata.json) ![GitHub](https://img.shields.io/github/license/sgibson91/bump-helm-deps-action) [![badge](https://img.shields.io/static/v1?label=Code%20of&message=Conduct&color=blueviolet)](CODE_OF_CONDUCT.md) [![badge](https://img.shields.io/static/v1?label=Contributing&message=Guidelines&color=blueviolet)](CONTRIBUTING.md)</center>

**Table of Contents:**

- [:mag: Overview](#mag-overview)
- [🤔 Assumptions `bump-helm-deps` Makes](#-assumptions-bump-helm-deps-makes)
- [:inbox_tray: Inputs](#inbox_tray-inputs)
- [:lock: Permissions](#lock-permissions)
- [:recycle: Example Usage](#recycle-example-usage)
- [:gift: Acknowledgements](#gift-acknowledgements)
- [:sparkles: Contributing](#sparkles-contributing)

---

## :mag: Overview

This is an overview of the steps the Action executes.

- Read the helm chart file and find the versions of the dependencies
- Scrape the helm chart source indexes and find the most recent version release for each dependency
- If there is a newer chart version available, then:
  - Create a new branch in the repository
  - Add the new version(s) to the helm chart file
  - Commit the file to the branch
  - Open a Pull Request to the default branch
  - Assign labels and reviewers to the Pull Request if required

A moderator should check and merge the Pull Request as appropriate.

## 🤔 Assumptions `bump-helm-deps` Makes

Here is a list detailing the assumptions that the Action makes.

1. You have a GitHub Token with enough permissions to access the GitHub API and create branches, commits and Pull Requests
2. The configuration for your helm chart is available in a **public** GitHub repository, or you have a token with sufficient permissions to read/write to a **private** repository
3. The dependent chart indexes are available at public URLs

## :inbox_tray: Inputs

| Variable | Description | Required? | Default Value |
| :--- | :--- | :--- | :--- |
| `chart_path` | The path to the file that stores the helm chart dependencies | :white_check_mark: | - |
| `chart_urls` | A string-serialised dictionary storing the location of the dependent and their versions. E.g. `'{"binderhub": "https://raw.githubusercontent.com/jupyterhub/helm-chart/gh-pages/index.yaml"}'` | :white_check_mark: | - |
| `github_token` | A GitHub token to make requests to the API with. Requires write permissions to: create new branches, make commits, and open Pull Requests. | :x: | `${{github.token}}` |
| `repository` | The GitHub repository where the helm chart is stored | :x: | `${{github.repository}}` |
| `base_branch` | The base branch to open the Pull Request against | :x: | `main` |
| `head_branch` | The branch to commit to and open a Pull Request from | :x: | `helm_dep_bump-WXYZ` where `WXYZ` will be a randomly generated ascii string (to avoid clashes) |
| `labels` | A comma-separated list of labels to apply to the opened Pull Request. Labels must already exist in the repository. | :x: | `[]` |
| `reviewers` | A comma-separated list of GitHub users (without the leading `@`) to request reviews from | :x: | `[]` |
| `dry_run` | Perform a dry-run of the action. A Pull Request will not be opened, but a log message will indicate if any helm chart versions can be bumped. | :x: | `False` |

## :lock: Permissions

This Action will need permission to read the contents of a file stored in your repository, create a new branch, commit to that branch, and open a Pull Request.
The [default permissive settings of `GITHUB_TOKEN`](https://docs.github.com/en/actions/security-guides/automatic-token-authentication#permissions-for-the-github_token) should provide the relevant permissions.

If instead your repository is using the default restricted settings of `GITHUB_TOKEN`, you could grant just enough permissions to the Action using a [`permissions`](https://docs.github.com/en/actions/learn-github-actions/workflow-syntax-for-github-actions#jobsjob_idpermissions) config, such as the one below:

```yaml
permissions:
  contents: write
  pull-requests: write
```

## :recycle: Example Usage

The simplest way to use the Action is documented below.
This config features a `workflow_dispatch` trigger to allow manual running whenever the maintainers desire, and a cron job trigger scheduled to run at 10am every weekday.

```yaml
name: Check and Bump Helm Chart Dependencies

on:
  workflow_dispath:
  schedule:
    - cron: "0 10 * * 1-5"

jobs:
  bump-helm-deps:
    runs-on: ubuntu-latest
    steps:
    - uses: sgibson91/bump-helm-deps-action@main
      with:
        chart_path: path/to/config
        chart_urls: '{"chart_1": "https://example.com/chart_1/index.yaml"}'
```

## :gift: Acknowledgements

Thank you to Christopher Hench ([@henchc](https://github.com/henchc)) who wrote and documented [`henchbot`](https://github.com/henchbot) which automatically opens Pull Requests to upgrade mybinder.org.
[Give his blog post a read!](https://hackmd.io/qC4ooA5TTn6xA2w-2OLHbA)

## :sparkles: Contributing

Thank you for wanting to contribute to the project! :tada:
Please read our [Code of Conduct](CODE_OF_CONDUCT.md) :purple_heart: and [Contributing Guidelines](CONTRIBUTING.md) :space_invader: to get you started.
