"""
Script to upgrade Helm Chart dependencies of the Hub23 chart
"""
import os
import time
import shutil
import logging
import requests
import subprocess

import numpy as np

from itertools import compress
from yaml import safe_load as load
from yaml import safe_dump as dump

from .run_command import run_cmd
from .CustomExceptions import AzureError, GitError


class HelmUpgradeBot:
    """Upgrade the dependencies of the Hub23 helm chart"""

    def __init__(self, argsDict):
        # Parse args from dict
        for k, v in argsDict.items():
            setattr(self, k, v)

        self.logging_setup(verbose=argsDict["verbose"])

        # Set the repo API
        self.repo_api = f"https://api.github.com/repos/{argsDict['repo_owner']}/{argsDict['repo_name']}/"

        # Initialise GitHub token, Chart info dict and clean up forked repo
        self.get_token(argsDict["token_name"])
        self.get_chart_versions()
        self.remove_fork()

        if argsDict["identity"]:
            # Set GitHub credentials for managed identity
            self.set_github_config()

    def check_versions(self):
        """Check if chart dependency versions are up-to-date"""

        charts = list(self.chart_info.keys())
        charts.remove(self.deployment)

        if self.dry_run:
            logging.info(
                "THIS IS A DRY-RUN. THE HELM CHART WILL NOT BE UPGRADED."
            )

        # Create conditions
        condition = [
            (
                self.chart_info[chart]["version"]
                != self.chart_info[self.deployment][chart]["version"]
            )
            for chart in charts
        ]

        if np.any(condition) and (not self.dry_run):
            logging.info(
                "Helm upgrade required for the following charts: %s"
                % list(compress(charts, condition))
            )
            self.upgrade_chart(list(compress(charts, condition)))
        elif np.any(condition) and self.dry_run:
            logging.info(
                "Helm upgrade required for the following charts: %s. PR won't be opened due to --dry-run flag being set."
                % list(compress(charts, condition))
            )
        else:
            logging.info(
                "%s is up-to-date with all current chart dependency releases!"
                % self.deployment
            )

    def add_commit_push(self, charts_to_update):
        """Perform git add, commit, push actions to an edited file"""

        logging.info("Adding file: %s" % self.fname)
        add_cmd = ["git", "add", self.fname]
        result = run_cmd(add_cmd)
        if result["returncode"] != 0:
            logging.error(result["err_msg"])
            self.clean_up()
            self.remove_fork()
            raise GitError(result["err_msg"])

        logging.info("Successfully added file: %s" % self.fname)

        commit_msg = f"Bump chart dependencies {[chart for chart in charts_to_update]} to versions {[self.chart_info[chart]['version'] for chart in charts_to_update]}, respectively"

        logging.info("Committing file: %s" % self.fname)
        commit_cmd = ["git", "commit", "-m", commit_msg]
        result = run_cmd(commit_cmd)
        if result["returncode"] != 0:
            logging.error(result["err_msg"])
            self.clean_up()
            self.remove_fork()
            raise GitError(result["err_msg"])

        logging.info("Successfully committed file: %s" % self.fname)

        logging.info("Pushing commits to branch: %s" % self.branch)
        push_cmd = [
            "git",
            "push",
            f"https://HelmUpgradeBot:{self.token}@github.com/HelmUpgradeBot/{self.repo_name}",
            self.branch,
        ]
        result = run_cmd(push_cmd)
        if result["returncode"] != 0:
            logging.error(result["err_msg"])
            self.clean_up()
            self.remove_fork()
            raise GitError(result["err_msg"])

        logging.info("Successfully pushed changes to branch: %s" % self.branch)

    def add_labels(self, url):
        """Adds labels to the Pull Request"""
        logging.info("Adding labels to PR: %s" % url)
        logging.info("Labels to be added: %s" % self.labels)

        labels_to_be_added = {"labels": self.labels}

        res = requests.post(
            url + "/labels",
            headers={"Authorization": f"token {self.token}"},
            json=labels_to_be_added,
        )

        if not res:
            logging.error(res.text)
            self.clean_up()
            self.remove_fork()
            raise GitError(res.text)

    def check_fork_exists(self):
        """Check if a fork of GitHub repo exists"""

        res = requests.get("https://api.github.com/users/HelmUpgradeBot/repos")

        if not res:
            logging.error(res.text)
            self.clean_up(self.repo_name)
            raise GitError(res.text)

        self.fork_exists = bool(
            [x for x in res.json() if x["name"] == self.repo_name]
        )

    def checkout_branch(self):
        """Checkout a branch of a GitHub repo"""

        if self.fork_exists:
            self.delete_old_branch()

            logging.info(
                "Pulling master branch of: %s/%s"
                % (self.repo_owner, self.repo_name)
            )
            pull_cmd = [
                "git",
                "pull",
                f"https://github.com/{self.repo_owner}/{self.repo_name}.git",
                "master",
            ]
            result = run_cmd(pull_cmd)
            if result["returncode"] != 0:
                logging.error(result["err_msg"])
                self.clean_up()
                self.remove_fork()
                raise GitError(result["err_msg"])

            logging.info(
                "Successfully pulled master branch of: %s/%s"
                % (self.repo_owner, self.repo_name)
            )

        logging.info("Checking out branch: %s" % self.branch)
        chkt_cmd = ["git", "checkout", "-b", self.branch]
        result = run_cmd(chkt_cmd)
        if result["returncode"] != 0:
            logging.error(result["err_msg"])
            self.clean_up()
            self.remove_fork()
            raise GitError(result["err_msg"])

        logging.info("Successfully checked out branch: %s" % self.branch)

    def clean_up(self):
        """Clean up cloned repo"""

        cwd = os.getcwd()
        this_dir = cwd.split("/")[-1]
        if this_dir == self.repo_name:
            os.chdir(os.pardir)

        if os.path.exists(self.repo_name):
            logging.info("Deleting local repository: %s" % self.repo_name)
            shutil.rmtree(self.repo_name)
            logging.info("Deleted local repository: %s" % self.repo_name)

    def clone_fork(self):
        """Clone a fork of a GitHub repo"""

        logging.info("Cloning fork: %s" % self.repo_name)

        clone_cmd = [
            "git",
            "clone",
            f"https://github.com/HelmUpgradeBot/{self.repo_name}.git",
        ]
        result = run_cmd(clone_cmd)
        if result["returncode"] != 0:
            logging.error(result["err_msg"])
            self.clean_up()
            self.remove_fork()
            raise GitError(result["err_msg"])

        logging.info("Successfully cloned repo: %s" % self.repo_name)

    def create_update_pr(self):
        """Open a Pull Request to the original repo on GitHub"""

        logging.info("Creating Pull Request")

        pr = {
            "title": "Logging Helm Chart version upgrade",
            "body": "This PR is updating the local Helm Chart to the most recent Chart dependency versions.",
            "base": "master",
            "head": f"HelmUpgradeBot:{self.branch}",
        }

        res = requests.post(
            self.repo_api + "pulls",
            headers={"Authorization": f"token {self.token}"},
            json=pr,
        )

        if not res:
            logging.error(res.text)
            self.clean_up()
            self.remove_fork()
            raise GitError(res.text)

        logging.info("Pull Request created")

        if self.labels is not None:
            output = res.json()
            self.add_labels(output["issue_url"])

    def delete_old_branch(self):
        """Delete a branch of a GitHub repo"""

        res = requests.get(
            f"https://api.github.com/repos/HelmUpgradeBot/{self.repo_name}/branches"
        )

        if not res:
            logging.error(res.text)
            raise GitError(res.text)

        if self.branch in [x["name"] for x in res.json()]:
            logging.info("Deleting branch: %s" % self.branch)

            delete_cmd = ["git", "push", "--delete", "origin", self.branch]
            result = run_cmd(delete_cmd)
            if result["returncode"] != 0:
                logging.error(result["err_msg"])
                self.clean_up()
                self.remove_fork()
                raise GitError(result["err_msg"])

            logging.info(
                "Successfully deleted remote branch: %s" % self.branch
            )

            delete_cmd = ["git", "branch", "-d", self.branch]
            result = run_cmd(delete_cmd)
            if result["returncode"] != 0:
                logging.error(result["err_msg"])
                self.clean_up()
                self.remove_fork()
                raise GitError(result["err_msg"])

            logging.info("Successfully deleted local branch: %s" % self.branch)

        else:
            logging.info("Branch does not exist: %s" % self.branch)

    def get_chart_versions(self):
        """Get versions of dependent charts"""

        self.chart_info = {}
        chart_urls = {
            self.deployment: f"https://raw.githubusercontent.com/{self.repo_owner}/{self.repo_name}/master/{self.chart_name}/requirements.yaml",
            "binderhub": "https://raw.githubusercontent.com/jupyterhub/helm-chart/gh-pages/index.yaml",
            "nginx-ingress": "https://raw.githubusercontent.com/helm/charts/master/stable/nginx-ingress/Chart.yaml",
        }

        for chart in chart_urls.keys():

            if chart == self.deployment:
                # Hub23 local chart info
                self.chart_info[self.deployment] = {}
                chart_reqs = load(
                    requests.get(chart_urls[self.deployment]).text
                )

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
                    key=lambda k: k["created"],
                )
                self.chart_info["binderhub"]["version"] = updates_sorted[-1][
                    "version"
                ]

            else:
                self.chart_info[chart] = {}
                chart_reqs = load(requests.get(chart_urls[chart]).text)
                self.chart_info[chart]["version"] = chart_reqs["version"]

    def get_token(self, token_name):
        """Get GitHub Access Token from Azure Key Vault"""

        self.login()

        logging.info("Retrieving secret: %s" % token_name)
        vault_cmd = [
            "az",
            "keyvault",
            "secret",
            "show",
            "-n",
            token_name,
            "--vault-name",
            self.keyvault,
            "--query",
            "value",
            "-o",
            "tsv",
        ]
        result = run_cmd(vault_cmd)
        if result["returncode"] != 0:
            logging.error(result["err_msg"])
            raise AzureError(result["err_msg"])

        self.token = result["output"].strip("\n")
        logging.info("Successfully pulled secret: %s" % token_name)

    def logging_setup(self, verbose=False):
        # Setup log config
        if verbose:
            logging.basicConfig(
                level=logging.DEBUG,
                format="[%(asctime)s %(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        else:
            logging.basicConfig(
                level=logging.DEBUG,
                filename="HelmUpgradeBot.log",
                filemode="a",
                format="[%(asctime)s %(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

    def login(self):
        """Login to Azure"""
        login_cmd = ["az", "login"]

        if self.identity:
            login_cmd.append("--identity")
            logging.info("Login to Azure with Managed System Identity")
        else:
            logging.info("Login to Azure")

        result = run_cmd(login_cmd)
        if result["returncode"] != 0:
            logging.error(result["err_msg"])
            raise AzureError(result["err_msg"])

        logging.info("Successfully logged into Azure")

    def make_fork(self):
        """Fork a GitHub repo"""
        logging.info("Forking repo: %s" % self.repo_name)
        res = requests.post(
            self.repo_api + "forks",
            headers={"Authorization": f"token {self.token}"},
        )

        if not res:
            logging.error(res.text)
            raise GitError(res.text)

        self.fork_exists = True
        logging.info("Created fork: %s" % self.repo_name)

    def remove_fork(self):
        """Delete a fork of a GitHub repo"""

        self.check_fork_exists()

        if self.fork_exists:
            logging.info("HelmUpgradeBot has a fork of: %s" % self.repo_name)
            res = requests.delete(
                f"https://api.github.com/repos/HelmUpgradeBot/{self.repo_name}",
                headers={"Authorization": f"token {self.token}"},
            )
            if not res:
                logging.error(res.text)
                raise GitError(res.text)

            self.fork_exists = False
            time.sleep(5)
            logging.info("Deleted fork: %s" % self.repo_name)

        else:
            logging.info(
                "HelmUpgradeBot does not have a fork of: %s" % self.repo_name
            )

    def set_github_config(self):
        """Set up GitHub configuration for API calls"""

        logging.info("Setting up git configuration for HelmUpgradeBot")

        subprocess.check_call(
            ["git", "config", "--global", "user.name", "HelmUpgradeBot"]
        )
        subprocess.check_call(
            [
                "git",
                "config",
                "--global",
                "user.email",
                "helmupgradebot.github@gmail.com",
            ]
        )

    def update_local_chart(self, charts_to_update):
        """Update the local helm chart"""

        logging.info("Updating local Helm Chart: %s" % self.chart_name)

        self.fname = os.path.join(self.chart_name, "requirements.yaml")
        with open(self.fname, "r") as f:
            chart_yaml = load(f)

        for chart in charts_to_update:
            for dependency in chart_yaml["dependencies"]:
                if dependency["name"] == chart:
                    dependency["version"] = self.chart_info[chart]["version"]

        with open(self.fname, "w") as f:
            dump(chart_yaml, f)

        logging.info("Updated file: %s" % self.fname)

    def upgrade_chart(self, charts_to_update):
        """Update the dependencies in the helm chart"""

        if not self.fork_exists:
            self.make_fork()
        self.clone_fork()

        if not self.dry_run:
            os.chdir(self.repo_name)
            self.checkout_branch()
            self.update_local_chart(charts_to_update)
            self.add_commit_push(charts_to_update)
            self.create_update_pr()

        self.clean_up()
