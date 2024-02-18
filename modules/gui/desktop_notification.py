from pathlib import Path

from notifypy import Notify

from modules.console import console
from modules.context import context
from modules.sprites import choose_random_sprite
from modules.version import pokebot_name, pokebot_version


def desktop_notification(title: str, message: str, icon: Path = None) -> None:
    if not context.config.logging.desktop_notifications:
        return

    try:
        icon = icon or choose_random_sprite()

        notification = Notify(
            default_notification_application_name=f"{context.profile.path.name} | {pokebot_name} {pokebot_version}"
        )
        notification.title = title
        notification.message = message
        notification.icon = icon

        notification.send()
    except Exception:
        console.print_exception()
