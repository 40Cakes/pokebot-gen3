import plyer


def desktop_notification(title: str, message: str) -> None:
    plyer.notification.notify(title=title, message=message)
