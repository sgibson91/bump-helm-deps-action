import os
import sys
import time
import shutil
import datetime
import requests
import subprocess
import pandas as pd
from yaml import safe_load as load

# URLs
REPO_API = "https://api.github.com/repos/alan-turing-institute/hub23-deploy/"

# Environment Variables
TOKEN = os.environ.get("BOT_TOKEN")


class helmUpgradeBotHub23:
    def __init__(self):
        self.get_latest_versions()


    def check_helm_version(self):
        hub23_prs = requests.get(REPO_API + "pulls?state=open")
        helmUpgradeBot_prs = [x for x in hub23_prs.json() if x["user"]["login"] == "HelmUpgradeBot"]
        self.check_fork_exists()

        if (len(helmUpgradeBot_prs) == 0) and self.fork_exists:
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
            sys.exit(0)

        self.clean_up()

    def upgrade_helm_version(self):
        if not self.fork_exists:
            self.make_fork()
        self.clone_fork()
        os.chdir("hub23-deploy")

        # Make the config files
        subprocess.check_call(["chmod", "700", "make-config-files.sh"])
        subprocess.check_call(["./make-config-files.sh"])


    def check_fork_exists(self):
        res = requests.get("https://api.github.com/users/HelmUpgradeBot/repos")
        self.fork_exists = bool([x for x in res.json() if x["name"] == "hub23-deploy"])


    def make_fork(self):
        requests.post(
            REPO_API + "forks",
            headers={"Authorization": f"token {TOKEN}"}
        )


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


    def checkout_branch(self, existing_pr):
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
        self.version_info["helm_page"]["version"] = updates_sorted[-1]['version'].split('-')[-1]


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
