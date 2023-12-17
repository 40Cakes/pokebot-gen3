import plyer

from modules.version import pokebot_name, pokebot_version


def desktop_notification(title: str, message: str) -> None:
    plyer.notification.notify(app_name=f"{pokebot_name} {pokebot_version}", title=title, message=message)
