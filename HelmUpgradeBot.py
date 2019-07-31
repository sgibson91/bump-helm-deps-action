"""
Script to pull the latest Helm Chart deployment from:
https://jupyterhub.github.io/helm-chart/#development-releases-binderhub
and compare the latest release with the Hub23 changelog.

If Hub23 needs an upgrade, the script will perform the upgrade and open a pull
request documenting the new helm chart version in the changelog.
"""

import os
import sys
import stat
import time
import shutil
import logging
import datetime
import requests
import argparse
import subprocess
import pandas as pd
from yaml import safe_load as load

# Access token for GitHub API
TOKEN = os.environ.get("BOT_TOKEN")

# Setup logging config
logging.basicConfig(
    level=logging.DEBUG,
    filename="HelmUpgradeBot.log",
    filemode="a",
    format="[%(asctime)s %(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def parse_args():
    """Command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Upgrade the Helm Chart of a BinderHub deployment and update the changelog in the deployment GitHub repository"
    )

    parser.add_argument(
        "-o",
        "--repo-owner",
        type=str,
        default="alan-turing-institute",
        help="The GitHub repository owner"
    )
    parser.add_argument(
        "-n",
        "--repo-name",
        type=str,
        default="hub23-deploy",
        help="The deployment repository name"
    )
    parser.add_argument(
        "-b",
        "--branch",
        type=str,
        default="helm_chart_bump",
        help="The git branch name to commit to"
    )
    parser.add_argument(
        "-f",
        "--files",
        nargs="?",
        default=["changelog.txt"],
        help="The files that should be updated. The first should be the changelog file."
    )
    parser.add_argument(
        "-d",
        "--deployment",
        type=str,
        default="Hub23",
        help="The name of the deployed BinderHub"
    )

    return parser.parse_args()

def get_latest_versions(binderhub_name, changelog_file):
    """Get latest Helm Chart versions

    Parameters
    ----------
    binderhub_name
        String.
    changelog_file
        String.

    Returns
    -------
    version_info
        Dictionary.
    """
    version_info = {binderhub_name: {}, "helm_page": {}}

    logging.info(f"Fetching the latest Helm Chart version deployed on: {binderhub_name}")
    changelog_url = f"https://raw.githubusercontent.com/alan-turing-institute/hub23-deploy/master/{changelog_file}"
    changelog = load(requests.get(changelog_url).text)
    version_info[binderhub_name]["date"] = pd.to_datetime(list(changelog.keys())[-1])
    version_info[binderhub_name]["version"] = changelog[list(changelog.keys())[-1]]

    url_helm_chart = "https://raw.githubusercontent.com/jupyterhub/helm-chart/gh-pages/index.yaml"
    logging.info(f"Fetching the latest Helm Chart version from: {url_helm_chart}")
    helm_chart_yaml = load(requests.get(url_helm_chart).text)
    updates_sorted = sorted(
        helm_chart_yaml["entries"]["binderhub"],
        key=lambda k: k["created"]
    )
    version_info["helm_page"]["date"] = updates_sorted[-1]['created']
    version_info["helm_page"]["version"] = updates_sorted[-1]['version']

    logging.info(f"{binderhub_name}: {version_info[binderhub_name]['date']} {version_info[binderhub_name]['version']}")
    logging.info(f"Helm Chart page: {version_info['helm_page']['date']} {version_info['helm_page']['version']}")

    return version_info

def check_fork_exists(repo_name):
    """Check if fork exists

    Parameters
    ----------
    repo_name
        String.

    Returns
    -------
    fork_exists
        Boolean.
    """
    res = requests.get("https://api.github.com/users/HelmUpgradeBot/repos")
    fork_exists = bool([x for x in res.json() if x["name"] == repo_name])

    return fork_exists

def remove_fork(repo_name):
    """Remove fork

    Parameters
    ----------
    repo_name
        String.

    Returns
    -------
    fork_exists
        Boolean.
    """
    fork_exists = check_fork_exists(repo_name)

    if fork_exists:
        logging.info(f"HelmUpgradeBot has a fork of: {repo_name}")
        requests.delete(
            f"https://api.github.com/repos/HelmUpgradeBot/{repo_name}/",
            headers={"Authorization": f"token {TOKEN}"}
        )
        fork_exists = False
        time.sleep(5)
        logging.info(f"Deleted fork: {repo_name}")

    else:
        logging.info(f"HelmUpgradeBot does not have a fork of: {repo_name}")
        return fork_exists

def clone_fork(repo_name):
    """Clone fork

    Parameters
    ----------
    repo_name
        String.
    """
    logging.info(f"Cloning fork: {repo_name}")
    proc = subprocess.Popen(
        ["git", "clone", f"https://github.com/HelmUpgradeBot/{repo_name}.git"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    res = proc.communicate()
    if proc.returncode == 0:
        logging.info(f"Successfully cloned fork: {repo_name}")
    else:
        err_msg = res[1].decode(encoding="utf-8")
        logging.error(err_msg)

def make_fork(repo_api, repo_name):
    """Create a fork

    Parameters
    ----------
    repo_api
        String.
    repo_name
        String.

    Returns
    -------
    fork_exists
        Boolean.
    """
    logging.info(f"Forking repo: {repo_name}")
    requests.post(
        repo_api + "forks",
        headers={"Authorization": f"token {TOKEN}"}
    )
    fork_exists = True
    logging.info(f"Created fork: {repo_name}")

    return fork_exists

def set_github_config():
    subprocess.check_call([
        "git", "config", "user.name", "HelmUpgradeBot"
    ])
    subprocess.check_call([
        "git", "config", "user.email", "helmupgradebot.github@gmail.com"
    ])

def delete_old_branch(repo_name, branch):
    """Delete old git branch

    Parameters
    ----------
    repo_name
        String.
    branch
        String.
    """
    logging.info(f"Deleting branch: {branch}")
    req = requests.get(
        f"https://api.github.com/repos/HelmUpgradeBot/{repo_name}/branches"
    )

    if branch in [x["name"] for x in req.json()]:
        proc = subprocess.Popen(
            ["git", "push", "--delete", "origin", branch],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        res = proc.communicate()
        if proc.returncode == 0:
            logging.info(f"Successfully deleted remote branch: {branch}")
        else:
            err_msg = res[1].decode(encoding="utf-8")
            logging.error(err_msg)

        proc = subprocess.Popen(
            ["git", "branch", "-d", branch],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        res = proc.communicate()
        if proc.returncode == 0:
            logging.info(f"Successfully deleted local branch: {branch}")
        else:
            err_msg = res[1].decode(encoding="utf-8")
            logging.error(err_msg)

def checkout_branch(fork_exists, repo_owner, repo_name, branch):
    """Checkout a git branch

    Parameters
    ----------
    fork_exists
        Boolean.
    repo_owner
        String.
    repo_name
        String
    branch
        String.
    """
    if fork_exists:
        delete_old_branch(repo_name, branch)

        logging.info(f"Pulling master branch of: {repo_owner}/{repo_name}")
        proc = subprocess.Popen(
            [
                "git", "pull",
                f"https://github.com/{repo_owner}/{repo_name}.git",
                "master"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        proc.communicate()
        if proc.returncode == 0:
            logging.info(f"Successfully pulled master branch of: {repo_owner}/{repo_name}")
        else:
            err_msg = res[1].decode(Encoding="utf-8")
            logging.error(err_msg)

    logging.info(f"Checking out branch: {branch}")
    proc = subprocess.Popen(
        ["git", "checkout", "-b", branch],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    res = proc.communicate()
    if proc.returncode == 0:
        logging.info(f"Successfully checked out branch: {branch}")
    else:
        err_msg = res[1].decode(encoding="utf-8")
        logging.error(err_msg)

def update_changelog(fnames, version_info):
    """Update changelog file

    Parameters
    ----------
    fnames
        List of strings.
    version_info
        Dictionary.
    """
    for fname in fnames:
        logging.info(f"Updating file: {fname}")

        if fname == "changelog.txt":
            with open(fname, "a") as f:
                f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d')}: {version_info['helm_page']['version']}")
        else:
            raise Exception("Please provide a function call to handle your other files.")

        logging.info(f"Updated file: {fname}")

def add_commit_push(changed_files, version_info, repo_name, branch):
    """Add commit and push files

    Parameters
    ----------
    changed_files
        List of strings. Filenames to process.
    version_info
        Dictionary.
    repo_name
        String.
    branch
        String.
    """
    for f in changed_files:
        logging.info(f"Adding file: {f}")
        proc = subprocess.Popen(
            ["git", "add", f],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        res = proc.communicate()
        if proc.returncode == 0:
            logging.info(f"Successfully added file: {f}")
        else:
            err_msg = res[1].decode(encoding="utf-8")
            logging.error(err_msg)

        commit_msg = f"Log Helm Chart bump to version {version_info['helm_page']['version']}"

        logging.info(f"Committing file: {f}")
        proc = subprocess.Popen(
            ["git", "commit", "-m", commit_msg],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        res = proc.communicate()
        if proc.returncode == 0:
            logging.info(f"Successfully committed file: {f}")
        else:
            err_msg = res[1].decode(encoding="utf-8")
            logging.error(err_msg)

        logging.info(f"Pushing commits to branch: {branch}")
        proc = subprocess.Popen(
            [
                "git", "push",
                f"https://HelmUpgradeBot:{TOKEN}@github.com/HelmUpgradeBot/{repo_name}",
                branch
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        res = proc.communicate()
        if proc.returncode == 0:
            logging.info(f"Successfully pushed changes to branch: {branch}")
        else:
            err_msg = res[1].decode(encoding="utf-8")
            logging.error(err_msg)

def make_pr_body(version_info, binderhub_name):
    """Make PR body

    Parameters
    ----------
    version_info
        Dictionary.
    binderhub_name
        String.

    Returns
    -------
    body
        String.
    """
    logging.info("Writing Pull Request body")

    today = pd.Timestamp.now().tz_localize(None)
    body = "\n".join([
        "This PR is updating the CHANGELOG to reflect the most recent Helm Chart version bump.",
        f"It had been {(today - version_info[binderhub_name]['date']).days} days since the last upgrade."
    ])

    logging.info("Pull Request body written")

    return body

def create_update_pr(version_info, branch, repo_api, binderhub_name):
    """Create a PR

    Parameters
    ----------
    version_info
        Dictionary.
    branch
        String.
    repo_api
        String.
    binderhub_name
        String.
    """
    logging.info("Creating Pull Request")

    body = make_pr_body(version_info, binderhub_name)

    pr = {
        "title": "Logging Helm Chart version upgrade",
        "body": body,
        "base": "master",
        "head": f"HelmUpgradeBot:{branch}"
    }

    requests.post(
        repo_api + "pulls",
        headers={"Authorization": f"token {TOKEN}"},
        json=pr
    )

    logging.info("Pull Request created")

def clean_up(repo_name):
    """Delete local repo

    Parameters
    ----------
    repo_name
        String.
    """
    cwd = os.getcwd()
    this_dir = cwd.split("/")[-1]
    if this_dir == repo_name:
        os.chdir(os.pardir)

    logging.info(f"Deleting local repository: {repo_name}")
    shutil.rmtree(this_dir)
    logging.info(f"Deleted local repository: {repo_name}")

def main():
    args = parse_args()

    # Set API URL
    repo_api = f"https://api.github.com/repos/{args.repo_owner}/{args.repo_name}/"

    # Initial set-up
    set_github_config()
    version_info = get_latest_versions(args.deployment, args.files[0])
    fork_exists = remove_fork(args.repo_name)

    # Create conditions
    date_cond = (version_info["helm_page"]["date"] > version_info[args.deployment]["date"])
    version_cond = (version_info["helm_page"]["version"] != version_info[args.deployment]["version"])

    if date_cond and version_cond:
        logging.info("Helm upgrade required")

        # Forking repo
        if not fork_exists:
            fork_exists = make_fork(repo_api, args.repo_name)
        clone_fork(args.repo_name)
        os.chdir(args.repo_name)

        # Make shell scripts executable
        os.chmod("make-config-files.sh", 0o700)
        os.chmod("upgrade.sh", 0o700)

        # Generating config files
        logging.info(f"Generating configuration files for: {args.deployment}")
        proc = subprocess.Popen(
            ["./make-config-files.sh"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        res = proc.communicate()
        if proc.returncode == 0:
            logging.info(f"Successfully generated configuration files: {args.deployment}")
        else:
            err_msg = res[1].decode(encoding="utf-8")
            logging.error(err_msg)

        # Upgrading Helm Chart
        logging.info(f"Upgrading Helm Chart for: {args.deployment}")
        proc = subprocess.Popen(
            ["./upgrade.sh", version_info["helm_page"]["version"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        res = proc.communicate()
        if proc.returncode == 0:
            logging.info(f"Helm Chart successfully upgraded for: {args.deployment}")
        else:
            err_msg = res[1].decode(encoding="utf-8")
            logging.error(err_msg)

        checkout_branch(fork_exists, args.repo_owner, args.repo_name, args.branch)
        update_changelog(args.files, version_info)
        add_commit_push(args.files, version_info, args.repo_name, args.branch)
        create_update_pr(version_info, args.branch, repo_api, args.deployment)

    else:
        logging.info(f"{args.deployment} is up-to-date with current BinderHub Helm Chart release!")

        today = pd.Timestamp.now().tz_localize(None)

        if ((today - version_info["helm_page"]["date"]).days >= 7) and fork_exists:
            fork_exists = remove_fork(args.repo_name)

    clean_up(args.repo_name)

if __name__ == "__main__":
    main()
