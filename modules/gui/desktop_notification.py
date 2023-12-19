from pathlib import Path
from notifypy import Notify

from modules.sprites import choose_random_sprite
from modules.version import pokebot_name, pokebot_version


def desktop_notification(title: str, message: str, icon: Path = choose_random_sprite()) -> None:
    notification = Notify(default_notification_application_name=f"{pokebot_name} {pokebot_version}")
    notification.title = title
    notification.message = message
    notification.icon = icon
    notification.send()
