def desktop_notification(title: str, message: str) -> None:
    try:
        import plyer
        plyer.notification.notify(title=title, message=message)
    except ImportError:
        pass
