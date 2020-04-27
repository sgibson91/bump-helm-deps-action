# Contributing Guidelines

:space_invader: :tada: Thank you for contributing to the project! :tada: :space_invader:

The following is a set of guidelines for contributing to the project on GitHub.
These are mostly guidelines, not rules.
Use your best judgement and feel free to propose changes to this document in a Pull Request.

**Table of Contents**

- [:purple_heart: Code of Conduct](#purple_heart-code-of-conduct)
- [:question: What should I know before I get started?](#question-what-should-i-know-before-i-get-started)
- [:gift: How can I contribute?](#gift-how-can-i-contribute)
  - [:bug: Reporting Bugs](#bug-reporting-bugs)
  - [:sparkles: Requesting Features](#sparkles-requesting-features)
  - [:hatching_chick: Your First Contribution](#hatching_chick-your-first-contribution)
  - [:arrow_right: Pull Requests](#arrow_right-pull-requests)
- [:art: Styleguides](#art-styleguides)
  - [:snake: Python Styleguide](#snake-python-styleguide)
  - [:pencil: Markdown Styleguide](#pencil-markdown-styleguide)
- [:notebook: Additional Notes](#notebook-additional-notes)
  - [:label: Issue and Pull Request Labels](#label-issue-and-pull-request-labels)

---

## :purple_heart: Code of Conduct

This project and everyone participating in it is expected to abide by and uphold the [Code of Conduct](CODE_OF_CONDUCT.md).
Please report any unacceptable behaviour to [Dr Sarah Gibson](mailto:drsarahlgibson@gmail.com).

## :question: What should I know before I get started?

> TBA: This section should be updated with information relevant to the project.

## :gift: How can I contribute?

### :bug: Reporting Bugs

If something doesn't work the way you expect it to, please check it hasn't already been reported in the repository's issue tracker.
Bug reports should have the bug label, or have a title beginning with `[BUG]`.

If you can't find an issue already reporting your bug, then please feel free to open a new issue.
This repository has a [bug report template](.github/ISSUE_TEMPLATE/bug_report.md) to help you be as descriptive as possible so we can squash that bug! :muscle:

### :sparkles: Requesting Features

If there was something extra you'd like to see added, please check that the feature hasn't already been requested in the project's issue tracker.
Feature requests should have the enhancement label.
Please also check the closed issues to make sure the feature has not already been requested but the project maintainers decided against developing it.

If you find an open issue describing the feature you wish for, you can "+1" the issue by giving a thumbs up reaction on the **top comment of the issue**.
You may also leave any thoughts or offers for support as new comments on the issue.

If you don't find an issue describing your feature, please open a feature request.
This repository has a [feature request template](.github/ISSUE_TEMPLATE/feature_request.md) to help you map out the feature you'd like.

### :hatching_chick: Your First Contribution

Unsure where to start contributing?
Check out the good first issue and help wanted labels to see where the project is looking for input.

### :arrow_right: Pull Requests

A Pull Request is a means for [people to collaboratively review and work on changes](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-requests) before they are introduced into the base branch of the code base.

To prepare your contribution for review, please follow these steps:

1. [Fork this repository](https://help.github.com/en/github/getting-started-with-github/fork-a-repo)
2. [Create a new branch](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-and-deleting-branches-within-your-repository) on your fork
   1. Where possible and appropriate, please use the following convention when naming your branch: `<type>/<issue-number>/<short-description>`.
      For example, if your contribution is fixing a a typo that was flagged in issue number 11, your branch name would be as follows: `fix/11/typo`.
3. Edit files or add new ones!
4. [Open your Pull Request](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request-from-a-fork)
   1. This repository has a [pull request template](.github/PULL_REQUEST_TEMPLATE.md) which will help you summarise your contribution and help reviewers know where to focus their feedback.
      Please complete it where possible and appropriate.

Congratulations! :tada:
You are now a developer for the project! :space_invader:

The maintainers will then review your Pull Request and may ask for some changes.
Once you and the maintainers are happy, your contribution will be merged!

## :art: Styleguides

### :snake: Python Styleguide

When writing Python scripts for this repository, it is recommended that contributors use [black](https://github.com/psf/black) and [flake8](https://flake8.pycqa.org/en/latest/) for formatting and linting styles.
The repository has GitHub Actions to check files are conforming to this styleguide, though not doing so will not prevent your contribution from being merged.
These tools are used as the maintainers believe this makes the code easier to read and keeps consistent formatting as more people contribute to the project.

While flake8 commands can be [disabled](https://flake8.pycqa.org/en/latest/user/violations.html), we only recommend doing this for [specific lines](https://flake8.pycqa.org/en/latest/user/violations.html#in-line-ignoring-errors) in such cases where reformatting would produce "ugly code".
The maintainers retain final say on what is "ugly code" on a case-by-case basis.

### :pencil: Markdown Styleguide

Documentation files are written in [Markdown](https://guides.github.com/features/mastering-markdown/).

When writing Markdown, it is recommended to start a new sentence on a new line and define a new paragraph by leaving a single blank line.
(Check out the raw version of this file for an example!)
While the sentences will render as a single paragraph; when suggestions are made on Pull Requests, the GitHub User Interface will only highlight the affected sentence - not the whole paragraph.
This makes reviews much easier to read!

## :notebook: Additional Notes

### :label: Issue and Pull Request Labels

Issues and Pull Requests can have labels assigned to them which indicate at a glance what aspects of the project they describe.
It is also possible to [sort issues by label](https://help.github.com/en/github/managing-your-work-on-github/filtering-issues-and-pull-requests-by-labels) making it easier to track down specific issues.
Below is a table with the currently used labels in the repo.

| Label | Description |
| :--- | :--- |
| `bug` | Something isn't working |
| `documentation` | Improvements or additions to the documentation |
| `enhancement` | New feature or request |
| `good first issue` | Good for newcomers |
| `help wanted` | Extra attention is needed |
