import os
import json
import time
import shutil
import logging
import requests
import argparse
import pandas as pd
from CustomExceptions import *
from run_command import run_cmd
from yaml import safe_load as load
from yaml import safe_dump as dump

# Setup log config
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
        "-d",
        "--deployment",
        type=str,
        default="hub23",
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
        "-c",
        "--chart-name",
        type=str,
        default="hub23-chart",
        help="Name of local Helm Chart"
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

def get_chart_versions(repo_owner, repo_name, binderhub_name, chart_name):
    """Function to get version numbers of hub23 local chart and all it's
    dependencies

    Parameters
    ----------
    repo_owner: string
    repo_name: string
    binderhub_name: string
    chart_name: string

    Returns
    -------
    chart_info: dictionary
    """
    chart_info = {}
    chart_urls = {
        binderhub_name: f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/refactor-to-chart/{chart_name}/requirements.yaml",
        "binderhub": "https://raw.githubusercontent.com/jupyterhub/helm-chart/gh-pages/index.yaml"
    }

    # Hub23 local chart info
    chart_info["hub23"] = {}
    chart_reqs = load(requests.get(chart_urls["hub23"]).text)

    for dependency in chart_reqs["dependencies"]:
        chart_info["hub23"][dependency["name"]] = {
            "version": dependency["version"]
        }

    # BinderHub chart
    chart_info["binderhub"] = {}
    chart_reqs = load(requests.get(chart_urls["binderhub"]).text)
    updates_sorted = sorted(
        chart_reqs["entries"]["binderhub"],
        key=lambda k: k["created"]
    )
    chart_info["binderhub"]["version"] = updates_sorted[-1]["version"]

    return chart_info

def get_token(token_name, keyvault, identity=False):
    """Get personal access token from Azure Key Vault

    Parameters
    ----------
    token_name: string
    keyvault: string
    identity: boolean

    Returns
    -------
    token: string
    """
    login_cmd = ["az", "login"]
    if identity:
        login_cmd.append("--identity")
        logging.info("Login to Azure with Managed System Identity")
    else:
        logging.info("Login to Azure")

    result = run_cmd(login_cmd)
    if result["returncode"] == 0:
        logging.info("Successfully logged into Azure")
    else:
        logging.error(result["err_msg"])
        raise AzureError(result["err_msg"])

    logging.info(f"Retrieving secret: {token_name}")
    get_token_cmd = [
        "az", "keyvault", "secret", "show", "-n", token_name, "--vault-name",
        keyvault
    ]
    result = run_cmd(get_token_cmd)
    if result["returncode"] == 0:
        logging.info(f"Successfully retrieved secret: {token_name}")
        secret_info = json.loads(result["output"])
        return secret_info["value"]
    else:
        logging.error(result["err_msg"])
        raise AzureError(result["err_msg"])

def set_github_config():
    import subprocess

    subprocess.check_call(["git", "config", "user.name", "HelmUpgradeBot"])
    subprocess.check_call([
        "git", "config", "user.email", "helmupgradebot.github@gmail.com"
    ])

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
            clean_up(repo_name)
            raise GitError(res.text)

    else:
        logging.info(f"HelmUpgradeBot does not have a fork of: {repo_name}")

    return fork_exists

def make_fork(repo_api, repo_name, token):
    """Create a fork

    Parameters
    ----------
    repo_api: string
    repo_name: string
    token: string

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
        clean_up(repo_name)
        fork_exists = remove_fork(repo_name, token)
        raise GitError(res.text)

def clone_fork(repo_name, token):
    """Clone fork

    Parameters
    ----------
    repo_name: string
    token: string
    """
    logging.info(f"Cloning fork: {repo_name}")
    clone_cmd = ["git", "clone", f"https://github.com/HelmUpgradeBot/{repo_name}.git"]
    result = run_cmd(clone_cmd)
    if result["returncode"] == 0:
        logging.info(f"Successfully cloned fork: {repo_name}")
    else:
        logging.error(result["err_msg"])
        clean_up(repo_name)
        fork_exists = remove_fork(repo_name, token)
        raise GitError(result["err_msg"])

def install_requirements(repo_name, token):
    """Install repo requirements

    Parameters
    ----------
    repo_name: string
    token: string
    """
    logging.info(f"Installing requirements for: {repo_name}")
    pip_cmd = ["pip", "install", "-r", "requirements.txt"]
    result = run_cmd(pip_cmd)
    if result["returncode"] == 0:
        logging.info("Successfully installed repo requirements")
    else:
        logging.error(result["err_msg"])
        clean_up(repo_name)
        fork_exists = remove_fork(repo_name, token)
        raise Exception(result["err_msg"])

def make_fork(repo_api, repo_name, token):
    """Create a fork

    Parameters
    ----------
    repo_api: string
    repo_name: string
    token: string

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
    token: string
    """
    res = requests.get(
        f"https://api.github.com/repos/HelmUpgradeBot/{repo_name}/branches"
    )

    if res:
        if branch in [x["name"] for x in res.json()]:
            logging.info(f"Deleting branch: {branch}")

            push_cmd = ["git", "push", "--delete", "origin", branch]
            result = run_cmd(push_cmd)
            if result["returncode"] == 0:
                logging.info(f"Successfully deleted remote branch: {branch}")
            else:
                logging.error(result["err_msg"])
                clean_up(repo_name)
                fork_exists = remove_fork(repo_name, token)
                raise GitError(result["err_msg"])

            branch_cmd = ["git", "branch", "-d", branch]
            result = run_cmd(branch_cmd)
            if result["returncode"] == 0:
                logging.info(f"Successfully deleted local branch: {branch}")
            else:
                logging.error(result["err_msg"])
                clean_up(repo_name)
                fork_exists = remove_fork(repo_name, token)
                raise GitError(result["err_msg"])

        else:
            logging.info(f"Branch does not exist: {branch}")

    else:
        logging.error(res.text)
        clean_up(repo_name)
        fork_exists = remove_fork(repo_name, token)
        raise GitError(res.text)

def checkout_branch(fork_exists, repo_owner, repo_name, branch, token):
    """Checkout a git branch

    Parameters
    ----------
    fork_exists: boolean
    repo_owner: string
    repo_name: string
    branch: string
    token: string
    """
    if fork_exists:
        delete_old_branch(repo_name, branch, token)

        logging.info(f"Pulling master branch of: {repo_owner}/{repo_name}")
        pull_cmd = [
            "git", "pull",
            f"https://github.com/{repo_owner}/{repo_name}.git",
            "master"
        ]
        result = run_cmd(pull_cmd)
        if result['returncode'] == 0:
            logging.info(f"Successfully pulled master branch of: {repo_owner}/{repo_name}")
        else:
            logging.error(result["err_msg"])
            clean_up(repo_name)
            fork_exists = remove_fork(repo_name, token)
            raise GitError(result["err_msg"])

    logging.info(f"Checking out branch: {branch}")
    chkt_cmd = ["git", "checkout", "-b", branch]
    result = run_cmd(chkt_cmd)
    if result["returncode"] == 0:
        logging.info(f"Successfully checked out branch: {branch}")
    else:
        logging.error(result["err_msg"])
        clean_up(repo_name)
        fork_exists = remove_fork(repo_name, token)
        raise GitError(result["err_msg"])

def update_local_chart(chart_name, repo_name, version_info):
    """Update changelog file

    Parameters
    ----------
    chart_name: string
    version_info: dictionary

    Returns
    -------
    fname: string
    """
    logging.info(f"Updating local Helm Chart: {chart_name}")

    fname = os.path.join(f"{chart_name}", "requirements.yaml")
    with open(fname, "r") as f:
        chart_yaml = load(f)

    for dependency in chart_yaml["dependencies"]:
        if dependency["name"] == "binderhub":
            dependency["version"] = version_info["binderhub"]

    with open(fname, "w") as f:
        dump(chart_yaml, f)

    logging.info(f"Updated file: {fname}")

    return fname

def add_commit_push(changed_file, version_info, repo_name, branch, token):
    """Add commit and push files

    Parameters
    ----------
    changed_file: string
    version_info: dictionary
    repo_name: string
    branch: string
    token: string
    """
    add_cmd = ["git", "add", changed_file]

    logging.info(f"Adding file: {changed_file}")
    result = run_cmd(add_cmd)
    if result["returncode"] == 0:
        logging.info(f"Successfully added file: {changed_file}")
    else:
        logging.error(result["err_msg"])
        clean_up(repo_name)
        fork_exists = remove_fork(repo_name, token)
        raise GitError(result["err_msg"])

    commit_msg = f"Log Helm Chart bump to version {version_info['binderhub']}"
    cmt_cmd = ["git", "commit", "-m", commit_msg]

    logging.info(f"Committing file: {changed_file}")
    result = run_cmd(cmt_cmd)
    if result["returncode"] == 0:
        logging.info(f"Successfully committed file: {changed_file}")
    else:
        logging.error(result["err_msg"])
        clean_up(repo_name)
        fork_exists = remove_fork(repo_name, token)
        raise GitError(result["err_msg"])

    logging.info(f"Pushing commits to branch: {branch}")
    push_cmd = [
        "git", "push",
        f"https://HelmUpgradeBot:{token}@github.com/HelmUpgradeBot/{repo_name}",
        branch
    ]
    result = run_cmd(push_cmd)
    if result["returncode"] == 0:
        logging.info(f"Successfully pushed changes to branch: {branch}")
    else:
        logging.error(result["err_msg"])
        clean_up(repo_name)
        fork_exists = remove_fork(repo_name, token)
        raise GitError(result["err_msg"])

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
        f"This PR is updating the {binderhub_name} local Helm Chart to pull the most recent BinderHub Helm Chart release.\n\n" +
        f"{version_info['hub23']} ... {version_info['binderhub']}"
    ])

    logging.info("Pull Request body written")

    return body

def create_update_pr(version_info, branch, repo_api, binderhub_name, token, repo_name):
    """Create a Pull Request

    Parameters
    ----------
    version_info: dictionary
    branch: string
    repo_api: string
    binderhub_name: string
    token: string
    repo_name: string
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
        fork_exists = remove_fork(repo_name, token)
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

    if os.path.exists(repo_name):
        logging.info(f"Deleting local repository: {repo_name}")
        shutil.rmtree(repo_name)
        logging.info(f"Deleted local repository: {repo_name}")

def main():
    args = parse_args()

    if args.dry_run:
        logging.info("THIS IS A DRY-RUN. THE HELM CHART WILL NOT BE UPGRADED.")

    chart_info = get_chart_versions(
        args.repo_owner,
        args.repo_name,
        args.deployment,
        args.chart_name
    )
    cond = (
        chart_info["hub23"]["binderhub"]["version"] ==
        chart_info["binderhub"]["version"]
    )

    if cond:
        logging.info("Hub23 is up-to-date with BinderHub!")
    else:
        version_info = {
            "hub23": chart_info["hub23"]["binderhub"]["version"],
            "binderhub": chart_info["binderhub"]["version"]
        }
        logging.info(f"""Helm upgrade required
    Hub23: {version_info['hub23']}
    BinderHub: {version_info['binderhub']}""")

        # Set API URL
        repo_api = f"https://api.github.com/repos/{args.repo_owner}/{args.repo_name}/"

        # Get access token from Azure Key Vault and remove fork
        token = get_token(args.token_name, args.keyvault, identity=args.identity)
        fork_exists = remove_fork(args.repo_name, token)

        if not args.dry_run:
            set_github_config()

        # Forking repo
        if not fork_exists:
            fork_exists = make_fork(repo_api, args.repo_name, token)
        clone_fork(args.repo_name, token)
        os.chdir(args.repo_name)
        install_requirements(args.repo_name, token)

        if not args.dry_run:
            checkout_branch(fork_exists, args.repo_owner, args.repo_name, args.branch, token)
            fname = update_local_chart(args.chart_name, args.repo_name, version_info)
            add_commit_push(args.files, version_info, args.repo_name, args.branch, token)
            create_update_pr(version_info, args.branch, repo_api, args.deployment, token, args.repo_name)

    clean_up(args.repo_name)
    fork_exists = remove_fork(args.repo_name, token)

if __name__ == "__main__":
    main()
