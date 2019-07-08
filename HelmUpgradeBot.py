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
import datetime
import requests
import subprocess
import pandas as pd
from yaml import safe_load as load

# Hub23 repo API URL
REPO_API = "https://api.github.com/repos/alan-turing-institute/hub23-deploy/"

# Access token for GitHub API
TOKEN = os.environ.get("BOT_TOKEN")


class helmUpgradeBotHub23:
    def __init__(self):
        self.get_latest_versions()


    def check_helm_version(self):
        self.check_fork_exists()

        if self.fork_exists:
            self.remove_fork()

        date_cond = (self.version_info["helm_page"]["date"] >
                     self.version_info["hub23"]["date"])
        version_cond = (self.version_info["helm_page"]["version"] !=
                        self.version_info["hub23"]["version"])

        if date_cond and version_cond:
            # Perform a Helm Chart upgrade
            print("Helm upgrade required")
            self.upgrade_helm_version()
        else:
            print("Hub23 is up-to-date with current BinderHub Helm Chart release!")

            today = pd.to_datetime(datetime.datetime.today().strftime("%Y-%m-%d"))

            if ((today - self.version_info["helm_page"]["date"]).days >= 7) and self.fork_exists:
                self.remove_fork()

            sys.exit(0)

        self.clean_up()

    def upgrade_helm_version(self):
        if not self.fork_exists:
            self.make_fork()
        self.clone_fork()
        os.chdir("hub23-deploy")

        # Make shell scripts executable
        os.chmod("make-config-files.sh", stat.S_IXOTH)
        os.chmod("upgrade.sh", stat.S_IXOTH)

        # Make the config files
        print("Generating Hub23 configuration files...")
        subprocess.check_call(["./make-config-files.sh"])

        # Upgrade Hub23's Helm Chart
        print("Upgrading Hub23 helm chart...")
        subprocess.check_call([
            "./upgrade.sh",
            f"{self.version_info['helm_page']['version']}"
        ])

        self.checkout_branch()
        fname = self.update_changelog()
        self.add_commit_push(fname)
        self.create_update_pr()


    def check_fork_exists(self):
        res = requests.get("https://api.github.com/users/HelmUpgradeBot/repos")
        self.fork_exists = bool([x for x in res.json() if x["name"] == "hub23-deploy"])


    def make_fork(self):
        requests.post(
            REPO_API + "forks",
            headers={"Authorization": f"token {TOKEN}"}
        )
        self.fork_exists = True


    def clone_fork(self):
    	subprocess.check_call([
            "git", "clone",
            "https://github.com/HelmUpgradeBot/hub23-deploy.git"
    	])


    def remove_fork(self):
        requests.delete(
            "https://api.github.com/repos/HelmUpgradeBot/hub23-deploy/",
            headers={"Authorization": f"token {TOKEN}"}
        )
        self.fork_exists = False
        time.sleep(5)


    def checkout_branch(self):
    	if self.fork_exists:
            self.delete_old_branch()
            subprocess.check_call([
                "git", "pull",
                "https://github.com/alan-turing-institute/hub23-deploy.git",
                "master"
    		])
    	subprocess.check_call([
            "git", "checkout", "-b", "helm_chart_bump"
    	])


    def delete_old_branch(self):
        res = requests.get(
	    	"https://api.github.com/repos/HelmUpgradeBot/hub23-deploy/branches"
	    )
        if "helm_chart_bump" in [x["name"] for x in res.json()]:
            subprocess.check_call([
                "git", "push", "--delete", "origin", "helm_chart_bump"
	    	])
            subprocess.check_call([
                "git", "branch", "-d", "helm_chart_bump"
	    	])


    def add_commit_push(self, changed_files):
        for f in changed_files:
            subprocess.check_call(["git", "add", f])

        commit_msg = f"Log helm chart bump to version {self.version_info['helm_page']['version']}"

        subprocess.check_call(["git", "config", "user.name", "HelmUpgradeBot"])
        subprocess.check_call([
            "git", "config", "user.email", "helmupgradebot.github@gmail.com"
        ])
        subprocess.check_call(["git", "commit", "-m", commit_msg])
        subprocess.check_call([
            "git", "push",
            f"https://HelmUpgradeBot:{TOKEN}@github.com/HelmUpgradeBot/hub23-deploy",
            "helm_chart_bump"
        ])


    def update_changelog(self):
        fname = "changelog.txt"
        with open(fname, "a") as f:
            f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d')}: {self.version_info['helm_page']['version']}")

        return [fname]


    def make_pr_body(self):
        today = pd.to_datetime(datetime.datetime.today().strftime("%Y-%m-%d"))

        body = "\n".join([
            "This PR is updating the CHANGELOG to reflect the most recent Helm Chart version bump.",
            f"It had been {(today - self.version_info['hub23']['date']).days} days since the last upgrade."
        ])

        return body


    def create_update_pr(self):
        body = self.make_pr_body()

        pr = {
            "title": "Logging Helm Chart version upgrade",
            "body": body,
            "base": "master",
            "head": "HelmUpgradeBot:helm_chart_bump"
        }

        requests.post(
            REPO_API + "pulls",
            headers={"Authorization": f"token {TOKEN}"},
            json=pr
        )


    def get_hub23_latest(self):
        changelog_url = "https://raw.githubusercontent.com/alan-turing-institute/hub23-deploy/master/changelog.txt"
        changelog = load(requests.get(changelog_url).text)
        last_update_date = pd.to_datetime(list(changelog.keys())[-1])
        last_update_version = changelog[list(changelog.keys())[-1]]

        self.version_info["hub23"]["date"] = last_update_date
        self.version_info["hub23"]["version"] = last_update_version


    def get_helmPage_latest(self):
        url_helm_chart = "https://raw.githubusercontent.com/jupyterhub/helm-chart/gh-pages/index.yaml"
        helm_chart_yaml = load(requests.get(url_helm_chart).text)

        updates_sorted = sorted(
            helm_chart_yaml["entries"]["binderhub"],
            key=lambda k: k["created"]
		)
        self.version_info["helm_page"]["date"] = updates_sorted[-1]['created']
        self.version_info["helm_page"]["version"] = updates_sorted[-1]['version']


    def get_latest_versions(self):
        self.version_info = {"hub23": {}, "helm_page": {}}

        print("Fetching the latest Helm Chart version deployed on Hub23")
        self.get_hub23_latest()

        print(f"Fetching latest Helm Chart version")
        self.get_helmPage_latest()

        print(f"Hub23: {self.version_info['hub23']['date']} {self.version_info['hub23']['version']}")
        print(f"Helm Chart page: {self.version_info['helm_page']['date']} {self.version_info['helm_page']['version']}")


    def clean_up(self):
        cwd = os.getcwd()
        this_dir = cwd.split("/")[-1]
        if this_dir == "hub23-deploy":
            os.chdir("..")

        shutil.rmtree(this_dir)


if __name__ == "__main__":
    bot = helmUpgradeBotHub23()
    bot.check_helm_version()
