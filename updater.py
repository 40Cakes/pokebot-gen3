import datetime
import sys
from dataclasses import dataclass
from datetime import datetime
from urllib import request
from urllib.error import URLError
from zipfile import ZipFile

import requests

# This is not being used, but it needs to be imported because otherwise `modules.console`
# runs into a circular import issue.
from modules import exceptions

from modules.console import console
from modules.runtime import get_base_path
from modules.version import pokebot_version


@dataclass
class ReleaseInfo:
    tag_name: str
    release_url: str
    download_url: str
    download_filename: str
    created_at: datetime


def get_last_update_check_datetime() -> datetime | None:
    check_file_path = get_base_path() / ".last-update-check"
    if not check_file_path.is_file():
        return None

    try:
        with open(check_file_path, "r") as file:
            result = datetime.fromisoformat(file.read())
        return result
    except:
        return None


def get_most_recent_release_on_github() -> ReleaseInfo | None:
    try:
        response = requests.get("https://api.github.com/repos/40cakes/pokebot-gen3/releases/latest")
        if response.status_code != 200:
            return None
        data = response.json()
        created_at = datetime.fromisoformat(data["created_at"])
    except Exception as e:
        console.print(f"[bold yellow]Error while checking for updates:[/] [yellow]{str(e)}[/]")
        return None

    if (
        "html_url" in data
        and "assets" in data
        and len(data["assets"]) > 0
        and "browser_download_url" in data["assets"][0]
        and "name" in data["assets"][0]
    ):
        with open(get_base_path() / ".last-update-check", "w") as file:
            file.write(str(datetime.now()))

        return ReleaseInfo(
            tag_name=data["tag_name"],
            release_url=data["html_url"],
            download_url=data["assets"][0]["browser_download_url"],
            download_filename=data["assets"][0]["name"],
            created_at=created_at,
        )
    else:
        return None


def fetch_release_from_github(release_info: ReleaseInfo) -> bool:
    try:
        request.urlretrieve(release_info.download_url, get_base_path() / release_info.download_filename)
        return True
    except URLError as e:
        console.print(f"[bold yellow]Error while downloading update:[/] [yellow]{str(e)}[/]")
        return False


def extract_update_file(release_info: ReleaseInfo) -> bool:
    try:
        with ZipFile(get_base_path() / release_info.download_filename) as zip:
            zip.extractall(path=get_base_path())
        return True
    except Exception as e:
        console.print(f"[bold yellow]Error while extracting update:[/] [yellow]{str(e)}[/]")
        return False


def run_updater(ignore_last_update: bool = False) -> None:
    last_update = get_last_update_check_datetime()
    if ignore_last_update or last_update is None or datetime.now().timestamp() - last_update.timestamp() > 86400:
        release_info = get_most_recent_release_on_github()
        if release_info is not None and release_info.tag_name != pokebot_version:
            console.print("\n[green bold]There is a new update available![/]\n")
            console.print(
                f"The most recent version is [cyan bold]{release_info.tag_name}[/], released on [yellow]{str(release_info.created_at)}[/].\n"
            )
            response = input("Download now? [y/N] ")
            if response in ["y", "Y"]:
                if fetch_release_from_github(release_info):
                    if extract_update_file(release_info):
                        console.print("\n[green]Update successful![/]")
                        console.print("[green bold]Restart the bot to apply.[/]")
                        sys.exit(0)
            else:
                console.print("\n[yellow]Ignoring update.[/] Will ask again tomorrow.")
                console.print(
                    f"If you change your mind, you can manually download the update here: {release_info.release_url}\n"
                )
        elif ignore_last_update:
            console.print("No newer version found.")


if __name__ == "__main__":
    run_updater(ignore_last_update=True)
