import os
import time
import json
import time
import shutil
import logging
import requests
import argparse
import datetime
import numpy as np
import pandas as pd
from CustomExceptions import *
from itertools import compress
from run_command import run_cmd
from yaml import safe_load as load
from yaml import safe_dump as dump

# Setup log config
logging.basicConfig(
    level=logging.DEBUG,
    filename="HelmUpgradeBot_{}.log".format(
        datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ),
    filemode="a",
    format="[%(asctime)s %(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def parse_args():
    """Command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Upgrade the Helm Chart of a BinderHub Helm Chart in the deployment GitHub repository"
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

class HelmUpgradeBot(object):
    def __init__(self, argsDict):
        # Parse args from dict
        self.repo_owner = argsDict["repo_owner"]
        self.repo_name = argsDict["repo_name"]
        self.branch = argsDict["branch"]
        self.chart_name = argsDict["chart_name"]
        self.deployment = argsDict["deployment"]
        self.keyvault = argsDict["keyvault"]
        self.identity = argsDict["identity"]
        self.dry_run = argsDict["dry_run"]
        self.repo_api = f"https://api.github.com/repos/{argsDict['repo_owner']}/{argsDict['repo_name']}/"

        self.get_token(argsDict["token_name"])
        self.get_chart_versions()
        self.remove_fork()

        if argsDict["identity"]:
            self.set_github_config()

    def login(self):
        login_cmd = ["az", "login"]

        if self.identity:
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

    def get_token(self, token_name):
        self.login()

        logging.info(f"Retrieving secret: {token_name}")
        vault_cmd = [
            "az", "keyvault", "secret", "show", "-n", token_name,
            "--vault-name", self.keyvault, "--query", "value", "-o", "tsv"
        ]
        result = run_cmd(vault_cmd)
        if result["returncode"] == 0:
            self.token = result["output"].strip("\n")
            logging.info(f"Successfully pulled secret: {token_name}")
        else:
            logging.error(result["err_msg"])
            raise AzureError(result["err_msg"])

    def get_chart_versions(self):
        self.chart_info = {}
        chart_urls = {
            self.deployment: f"https://raw.githubusercontent.com/{self.repo_owner}/{self.repo_name}/master/{self.chart_name}/requirements.yaml",
            "binderhub": "https://raw.githubusercontent.com/jupyterhub/helm-chart/gh-pages/index.yaml",
            "nginx-ingress": "https://raw.githubusercontent.com/helm/charts/master/stable/nginx-ingress/Chart.yaml"
        }

        for chart in chart_urls.keys():

            if chart == self.deployment:
                # Hub23 local chart info
                self.chart_info[self.deployment] = {}
                chart_reqs = load(requests.get(chart_urls[self.deployment]).text)

                for dependency in chart_reqs["dependencies"]:
                    self.chart_info[self.deployment][dependency["name"]] = {
                        "version": dependency["version"]
                    }

            elif chart == "binderhub":
                # BinderHub chart
                self.chart_info["binderhub"] = {}
                chart_reqs = load(requests.get(chart_urls["binderhub"]).text)
                updates_sorted = sorted(
                    chart_reqs["entries"]["binderhub"],
                    key=lambda k: k["created"]
                )
                self.chart_info["binderhub"]["version"] = updates_sorted[-1]["version"]

            else:
                self.chart_info[chart] = {}
                chart_reqs = load(requests.get(chart_urls[chart]).text)
                self.chart_info[chart]["version"] = chart_reqs["version"]

    def set_github_config(self):
        logging.info("Setting up git configuration for HelmUpgradeBot")

        subprocess.check_call([
            "git", "config", "user.name", "HelmUpgradeBot"
        ])
        subprocess.check_call([
            "git", "config", "user.email", "helmupgradebot.github@gmail.com"
        ])

    def check_fork_exists(self):
        res = requests.get("https://api.github.com/users/HelmUpgradeBot/repos")

        if res:
            self.fork_exists = bool([x for x in res.json() if x["name"] == self.repo_name])
        else:
            logging.error(res.text)
            clean_up(repo_name)
            raise GitError(res.text)

    def remove_fork(self):
        self.check_fork_exists()

        if self.fork_exists:
            logging.info(f"HelmUpgradeBot has a fork of: {self.repo_name}")
            res = requests.delete(
                f"https://api.github.com/repos/HelmUpgradeBot/{self.repo_name}",
                headers={"Authorization": f"token {self.token}"}
            )
            if res:
                self.fork_exists = False
                time.sleep(5)
                logging.info(f"Deleted fork: {self.repo_name}")
            else:
                logging.error(res.text)
                raise GitError(res.text)

        else:
            logging.info(f"HelmUpgradeBot does not have a fork of: {self.repo_name}")

    def check_versions(self):
        charts = ["binderhub", "nginx-ingress"]

        if self.dry_run:
            logging.info("THIS IS A DRY-RUN. THE HELM CHART WILL NOT BE UPGRADED.")

        # Create conditions
        condition = [(self.chart_info[chart]["version"] !=
            self.chart_info[self.deployment][chart]["version"])
            for chart in charts]

        if np.any(condition):
            logging.info(f"Helm upgrade required for the following charts: {list(compress(charts, condition))}")
            # self.upgrade_chart()
        else:
            logging.info(f"{self.deployment} is up-to-date with current BinderHub Helm Chart release!")

    def upgrade_chart(self):
        # Forking repo
        if not self.fork_exists:
            self.make_fork()
        self.clone_fork()

        if not self.dry_run:
            os.chdir(self.repo_name)
            self.checkout_branch()
            self.update_local_chart()
            self.add_commit_push()
            self.create_update_pr()

        self.clean_up()
        # self.remove_fork()

    def make_fork(self):
        logging.info(f"Forking repo: {self.repo_name}")
        res = requests.post(
            self.repo_api + "forks",
            headers={"Authorization": f"token {self.token}"}
        )

        if res:
            self.fork_exists = True
            logging.info(f"Created fork: {self.repo_name}")
        else:
            logging.error(res.text)
            raise GitError(res.text)

    def clone_fork(self):
        logging.info(f"Cloning fork: {self.repo_name}")

        clone_cmd = [
            "git", "clone", f"https://github.com/HelmUpgradeBot/{self.repo_name}.git"
        ]
        result = run_cmd(clone_cmd)
        if result["returncode"] == 0:
            logging.info(f"Successfully cloned repo: {self.repo_name}")
        else:
            logging.error(result["err_msg"])
            self.clean_up()
            self.remove_fork()
            raise GitError(result["err_msg"])

    def delete_old_branch(self):
        res = requests.get(
            f"https://api.github.com/repos/HelmUpgradeBot/{self.repo_name}/branches"
        )

        if res:
            if self.branch in [x["name"] for x in res.json()]:
                logging.info(f"Deleting branch: {self.branch}")

                delete_cmd = ["git", "push", "--delete", "origin", self.branch]
                result = run_cmd(delete_cmd)
                if result["returncode"] == 0:
                    logging.info(f"Successfully deleted remote branch: {self.branch}")
                else:
                    logging.error(result["err_msg"])
                    self.clean_up()
                    self.remove_fork()
                    raise GitError(result["err_msg"])

                delete_cmd = ["git", "branch", "-d", self.branch]
                result = run_cmd(delete_cmd)
                if result["returncode"] == 0:
                    logging.info(f"Successfully deleted local branch: {self.branch}")
                else:
                    logging.error(result["err_msg"])
                    swlf.clean_up()
                    self.remove_fork()
                    raise GitError(result["err_msg"])

            else:
                logging.info(f"Branch does not exist: {self.branch}")

        else:
            logging.error(res.text)
            raise GitError(res.text)

    def checkout_branch(self):
        if self.fork_exists:
            self.delete_old_branch()

            logging.info(f"Pulling master branch of: {self.repo_owner}/{self.repo_name}")
            pull_cmd = [
                "git", "pull",
                f"https://github.com/{self.repo_owner}/{self.repo_name}.git",
                "master"
            ]
            result = run_cmd(pull_cmd)
            if result["returncode"] == 0:
                logging.info(f"Successfully pulled master branch of: {self.repo_owner}/{self.repo_name}")
            else:
                logging.error(result["err_msg"])
                self.clean_up()
                self.remove_fork()
                raise GitError(result["err_msg"])

        logging.info(f"Checking out branch: {self.branch}")
        chkt_cmd = ["git", "checkout", "-b", self.branch]
        result = run_cmd(chkt_cmd)
        if result["returncode"] == 0:
            logging.info(f"Successfully checked out branch: {self.branch}")
        else:
            logging.error(result["err_msg"])
            self.clean_up()
            self.remove_fork()
            raise GitError(result["err_msg"])

    def update_local_chart(self):
        logging.info(f"Updating local Helm Chart: {self.chart_name}")

        self.fname = f"{self.chart_name}/requirements.yaml"
        with open(self.fname, "r") as f:
            chart_yaml = load(f)

        for dependency in chart_yaml["dependencies"]:
            if dependency["name"] == "binderhub":
                dependency["version"] = self.chart_info["binderhub"]["version"]

        with open(self.fname, "w") as f:
            dump(chart_yaml, f)

        logging.info(f"Updated file: {self.fname}")

    def add_commit_push(self):
        logging.info(f"Adding file: {self.fname}")
        add_cmd = ["git", "add", self.fname]
        result = run_cmd(add_cmd)
        if result["returncode"] == 0:
            logging.info(f"Successfully added file: {self.fname}")
        else:
            logging.error(result["err_msg"])
            self.clean_up()
            self.remove_fork()
            raise GitError(result["err_msg"])

        commit_msg = f"Log Helm Chart bump to version {self.chart_info['binderhub']['version']}"

        logging.info(f"Committing file: {self.fname}")
        commit_cmd = ["git", "commit", "-m", commit_msg]
        result = run_cmd(commit_cmd)
        if result["returncode"] == 0:
            logging.info(f"Successfully committed file: {self.fname}")
        else:
            logging.error(result["err_msg"])
            self.clean_up()
            self.remove_fork()
            raise GitError(result["err_msg"])

        logging.info(f"Pushing commits to branch: {self.branch}")
        push_cmd = [
            "git", "push",
            f"https://HelmUpgradeBot:{self.token}@github.com/HelmUpgradeBot/{self.repo_name}",
            self.branch
        ]
        result = run_cmd(push_cmd)
        if result["returncode"] == 0:
            logging.info(f"Successfully pushed changes to branch: {self.branch}")
        else:
            logging.error(result["err_msg"])
            self.clean_up()
            self.remove_fork()
            raise GitError(result["err_msg"])

    def make_pr_body(self):
        logging.info("Writing Pull Request body")

        today = pd.Timestamp.now().tz_localize(None)
        body = "\n".join([
            "This PR is updating the local Helm Chart to the most recent BinderHub Helm Chart version."
        ])

        logging.info("Pull Request body written")

        return body

    def create_update_pr(self):
        logging.info("Creating Pull Request")

        body = self.make_pr_body()

        pr = {
            "title": "Logging Helm Chart version upgrade",
            "body": body,
            "base": "master",
            "head": f"HelmUpgradeBot:{self.branch}"
        }

        res = requests.post(
            self.repo_api + "pulls",
            headers={"Authorization": f"token {self.token}"},
            json=pr
        )

        if res:
            logging.info("Pull Request created")
        else:
            logging.error(res.text)
            self.clean_up()
            self.remove_fork()
            raise GitError(res.text)

    def clean_up(self):
        cwd = os.getcwd()
        this_dir = cwd.split("/")[-1]
        if this_dir == self.repo_name:
            os.chdir(os.pardir)

        if os.path.exists(self.repo_name):
            logging.info(f"Deleting local repository: {self.repo_name}")
            shutil.rmtree(self.repo_name)
            logging.info(f"Deleted local repository: {self.repo_name}")

if __name__ == "__main__":
    args = parse_args()
    bot = HelmUpgradeBot(vars(args))
    bot.check_versions()
