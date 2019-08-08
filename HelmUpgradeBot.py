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
import json
import shutil
import logging
import datetime
import requests
import argparse
import subprocess
import pandas as pd
from CustomExceptions import *
from yaml import safe_load as load

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
    parser.add_argument(
        "-t",
        "--token-name",
        type=str,
        default="HelmUpgradeBot-token",
        help="Name of bot PAT in Azure Key Vault"
    )
    parser.add_argument(
        "-v",
        "--keyvault",
        type=str,
        default="hub23-keyvault",
        help="Name of Azure Key Vault bot PAT is stored in"
    )
    parser.add_argument(
        "--identity",
        action="store_true",
        help="Login to Azure with a Managed System Identity"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry-run helm upgrade"
    )

    return parser.parse_args()

def get_token(keyvault, token_name, identity=False):
    """Get personal access token for bot from Azure Key Vault

    Parameters
    ----------
    keyvault: string
    token_name: string
    identity: boolean

    Returns
    -------
    token: string
    """
    login_cmd = ["az", "login"]
    if identity:
        login_cmd.append("--identity")
        logging.info("Logging into Azure using Managed System Identity")
    else:
       logging.info("Logging into Azure")

    proc = subprocess.Popen(
        login_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    res = proc.communicate()
    if proc.returncode == 0:
        logging.info("Successfully logged into Azure")
    else:
        err_msg = res[1].decode(encoding="utf-8")
        logging.error(err_msg)
        raise AzureError(err_msg)

    logging.info(f"Retrieving secret: {token_name}")
    proc = subprocess.Popen(
        ["az", "keyvault", "secret", "show", "-n", token_name, "--vault-name", keyvault],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    res = proc.communicate()
    if proc.returncode == 0:
        json_out = res[0].decode(encoding="utf-8")
        secret_info = json.loads(json_out)
        logging.info(f"Successfully retrieved secret: {token_name}")
        return secret_info["value"]
    else:
        err_msg = res[1].decode(encoding="utf-8")
        logging.error(err_msg)
        raise AzureError(err_msg)

def set_github_config():
    subprocess.check_call([
        "git", "config", "user.name", "HelmUpgradeBot"
    ])
    subprocess.check_call([
        "git", "config", "user.email", "helmupgradebot.github@gmail.com"
    ])

def get_latest_versions(binderhub_name, changelog_file):
    """Get latest Helm Chart versions

    Parameters
    ----------
    binderhub_name: string
    changelog_file: string

    Returns
    -------
    version_info: dictionary
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
    repo_name: string

    Returns
    -------
    fork_exists: boolean
    """
    res = requests.get("https://api.github.com/users/HelmUpgradeBot/repos")

    if res:
        fork_exists = bool([x for x in res.json() if x["name"] == repo_name])
        return fork_exists
    else:
        logging.error(res.text)
        raise GitError(res.text)

def remove_fork(repo_name, token):
    """Remove fork

    Parameters
    ----------
    repo_name: string
    token: string

    Returns
    -------
    fork_exists: boolean
    """
    fork_exists = check_fork_exists(repo_name)

    if fork_exists:
        logging.info(f"HelmUpgradeBot has a fork of: {repo_name}")
        res = requests.delete(
            f"https://api.github.com/repos/HelmUpgradeBot/{repo_name}",
            headers={"Authorization": f"token {token}"}
        )
        if res:
            fork_exists = False
            time.sleep(5)
            logging.info(f"Deleted fork: {repo_name}")
        else:
            logging.error(res.text)
            raise GitError(res.text)

    else:
        logging.info(f"HelmUpgradeBot does not have a fork of: {repo_name}")
        return fork_exists

def clone_fork(repo_name, token):
    """Clone fork

    Parameters
    ----------
    repo_name: string
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
        clean_up(repo_name)
        fork_exists = remove_fork(repo_name, token)
        raise GitError(err_msg)

def install_requirements(repo_name, token):
    """Install repo requirements

    Parameters
    ----------
    repo_name: string
    """
    logging.info(f"Installing requirements for: {repo_name}")

    proc = subprocess.Popen(
        ["pip", "install", "-r", "requirements.txt"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    res = proc.communicate()
    if proc.returncode == 0:
        logging.info("Successfully installed repo requirements")
    else:
        err_msg = res[1].decode(encoding="utf-8")
        logging.error(err_msg)
        clean_up(repo_name)
        fork_exists = remove_fork(repo_name, token)
        raise Exception(err_msg)

def make_fork(repo_api, repo_name, token):
    """Create a fork

    Parameters
    ----------
    repo_api: string
    repo_name: string.
    token: string.

    Returns
    -------
    fork_exists: boolean
    """
    logging.info(f"Forking repo: {repo_name}")
    res = requests.post(
        repo_api + "forks",
        headers={"Authorization": f"token {token}"}
    )

    if res:
        fork_exists = True
        logging.info(f"Created fork: {repo_name}")
        return fork_exists
    else:
        logging.error(res.text)
        raise GitError(res.text)

def delete_old_branch(repo_name, branch, token):
    """Delete old git branch

    Parameters
    ----------
    repo_name: string
    branch: string
    """
    res = requests.get(
        f"https://api.github.com/repos/HelmUpgradeBot/{repo_name}/branches"
    )

    if res:
        if branch in [x["name"] for x in res.json()]:
            logging.info(f"Deleting branch: {branch}")

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
                clean_up(repo_name)
                fork_exists = remove_fork(repo_name, token)
                raise GitError(err_msg)

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
                clean_up(repo_name)
                remove_fork(repo_name, token)
                raise GitError(err_msg)

        else:
            logging.info(f"Branch does not exist: {branch}")

    else:
        logged.error(res.text)
        raise GitError(res.text)

def checkout_branch(fork_exists, repo_owner, repo_name, branch, token):
    """Checkout a git branch

    Parameters
    ----------
    fork_exists: boolean
    repo_owner: string
    repo_name: string
    branch: string
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
            clean_up(repo_name)
            fork_exists = remove_fork(repo_name, token)
            raise GitError(err_msg)

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
        clean_up(repo_name)
        fork_exists = remove_fork(repo_name, token)
        raise GitError(err_msg)

def update_changelog(fnames, version_info):
    """Update changelog file

    Parameters
    ----------
    fnames: list of strings
    version_info: dictionary
    """
    for fname in fnames:
        logging.info(f"Updating file: {fname}")

        if fname == "changelog.txt":
            with open(fname, "a") as f:
                f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d')}: {version_info['helm_page']['version']}")
        else:
            logging.warning("Exception: Please provide a function call to handle your other files.")

        logging.info(f"Updated file: {fname}")

def add_commit_push(changed_files, version_info, repo_name, branch, token):
    """Add commit and push files

    Parameters
    ----------
    changed_files: list of strings. Filenames to process.
    version_info: dictionary
    repo_name: string
    branch: string
    token: string
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
            clean_up(repo_name)
            fork_exists = remove_fork(repo_name, token)
            raise GitError(err_msg)

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
            clean_up(repo_name)
            fork_exists = remove_fork(repo_name, token)
            raise GitError(err_msg)

        logging.info(f"Pushing commits to branch: {branch}")
        proc = subprocess.Popen(
            [
                "git", "push",
                f"https://HelmUpgradeBot:{token}@github.com/HelmUpgradeBot/{repo_name}",
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
            clean_up(repo_name)
            fork_exists = remove_fork(repo_name, token)
            raise GitError(err_msg)

def make_pr_body(version_info, binderhub_name):
    """Make Pull Request body

    Parameters
    ----------
    version_info: dictionary
    binderhub_name: string

    Returns
    -------
    body: string
    """
    logging.info("Writing Pull Request body")

    today = pd.Timestamp.now().tz_localize(None)
    body = "\n".join([
        "This PR is updating the CHANGELOG to reflect the most recent Helm Chart version bump.",
        f"It had been {(today - version_info[binderhub_name]['date']).days} days since the last upgrade."
    ])

    logging.info("Pull Request body written")

    return body

def create_update_pr(version_info, branch, repo_api, binderhub_name, token):
    """Create a Pull Request

    Parameters
    ----------
    version_info: dictionary
    branch: string
    repo_api: string
    binderhub_name: string
    token: string
    """
    logging.info("Creating Pull Request")

    body = make_pr_body(version_info, binderhub_name)

    pr = {
        "title": "Logging Helm Chart version upgrade",
        "body": body,
        "base": "master",
        "head": f"HelmUpgradeBot:{branch}"
    }

    res = requests.post(
        repo_api + "pulls",
        headers={"Authorization": f"token {token}"},
        json=pr
    )

    if res:
        logging.info("Pull Request created")
    else:
        logging.error(res.text)
        clean_up(repo_name)
        remove_fork(repo_name, token)
        raise GitError(res.text)

def clean_up(repo_name):
    """Delete local repo

    Parameters
    ----------
    repo_name: string
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

    if args.dry_run:
        logging.info("THIS IS A DRY-RUN. THE HELM CHART WILL NOT BE UPGRADED.")

    # Set API URL
    repo_api = f"https://api.github.com/repos/{args.repo_owner}/{args.repo_name}/"

    # Initial set-up
    token = get_token(args.keyvault, args.token_name, identity=args.identity)
    set_github_config()
    version_info = get_latest_versions(args.deployment, args.files[0])
    fork_exists = remove_fork(args.repo_name, token)

    # Create conditions
    date_cond = (version_info["helm_page"]["date"] > version_info[args.deployment]["date"])
    version_cond = (version_info["helm_page"]["version"] != version_info[args.deployment]["version"])

    if date_cond and version_cond:
        logging.info("Helm upgrade required")

        # Forking repo
        if not fork_exists:
            fork_exists = make_fork(repo_api, args.repo_name, token)
        clone_fork(args.repo_name, token)
        os.chdir(args.repo_name)
        install_requirements(args.repo_name, token)

        # Generating config files
        config_cmd = ["python", "generate-configs.py"]
        if args.identity:
            config_cmd.append("--identity")

        logging.info(f"Generating configuration files for: {args.deployment}")
        proc = subprocess.Popen(
            config_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        res = proc.communicate()
        if proc.returncode == 0:
            logging.info(f"Successfully generated configuration files: {args.deployment}")
        else:
            err_msg = res[1].decode(encoding="utf-8")
            logging.error(err_msg)
            clean_up(args.repo_name)
            remove_fork(args.repo_name, token)
            raise BashError(err_msg)

        # Upgrading Helm Chart
        upgrade_cmd = [
            "python", "upgrade.py", "-v", version_info["helm_page"]["version"],
        ]
        if args.identity:
            upgrade_cmd.append("--identity")
        if args.dry_run:
            logging.info("Adding --dry-run argument to Helm Upgrade")
            upgrade_cmd.append("--dry-run")

        logging.info(f"Upgrading Helm Chart for: {args.deployment}")
        proc = subprocess.Popen(
            upgrade_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        res = proc.communicate()
        if proc.returncode == 0:
            logging.info(f"Helm Chart successfully upgraded for: {args.deployment}")
        else:
            err_msg = res[1].decode(encoding="utf-8")
            logging.error(err_msg)
            clean_up(args.repo_name)
            remove_fork(args.repo_name, token)
            raise BashError(err_msg)

        if not args.dry_run:
            checkout_branch(fork_exists, args.repo_owner, args.repo_name, args.branch, token)
            update_changelog(args.files, version_info)
            add_commit_push(args.files, version_info, args.repo_name, args.branch, token)
            create_update_pr(version_info, args.branch, repo_api, args.deployment, token)

    else:
        logging.info(f"{args.deployment} is up-to-date with current BinderHub Helm Chart release!")

    clean_up(args.repo_name)
    fork_exists = remove_fork(args.repo_name, token)

if __name__ == "__main__":
    main()
