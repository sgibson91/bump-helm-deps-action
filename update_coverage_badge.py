import json
import os
import argparse

from bs4 import BeautifulSoup
from rich import print

HERE = os.getcwd()


def get_current_percent(filename):
    filepath = os.path.join(HERE, filename)

    with open(filepath, "r") as stream:
        body = json.load(stream)

    return int(body["message"].strip("%"))


def get_new_percent():
    filepath = os.path.join(HERE, "htmlcov", "index.html")

    with open(filepath, "r") as f:
        text = f.read()
    soup = BeautifulSoup(text, "html.parser")

    span = soup.find_all("span", attrs={"class": "pc_cov"})[0]

    return int(span.text.strip("%"))


def update_json(percent, filename):
    filepath = os.path.join(HERE, filename)

    with open(filepath, "r") as stream:
        body = json.load(stream)

    body["message"] = f"{percent}%"

    if percent < 60:
        body["color"] = "red"
    elif (percent >= 60) and (percent < 80):
        body["color"] = "orange"
    else:
        body["color"] = "green"

    with open(filepath, "w") as stream:
        json.dump(body, stream, indent=4, sort_keys=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", choices=["true", "false"])
    args = parser.parse_args()

    filename = "badge_metadata.json"

    current = get_current_percent(filename)
    new = get_new_percent()

    if current == new:
        print("No change in coverage percentage! :tada:")

    else:
        diff = new - current

        if diff > 0:
            print(f"Coverage has [bold green]increased[/bold green] by {abs(diff)}% :white_check_mark:")
        else:
            print(f"Coverage has [bold red]decreased[/bold red] by {abs(diff)}% :x:")

        if args.dry_run == "false":
            update_json(new, filename)


if __name__ == "__main__":
    main()
