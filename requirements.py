import io
import pip
import pathlib
import platform
import sys
import zipfile

libmgba_tag = "0.2.0-2"
libmgba_ver = "0.2.0"

modules_all = [
    "numpy~=1.25.2",
    "Flask~=2.3.2",
    "Flask-Cors~=4.0.0",
    "ruamel.yaml~=0.17.32",
    "pypresence~=4.3.0",
    "obsws-python~=1.6.0",
    "pandas~=2.0.3",
    "discord-webhook~=1.2.1",
    "jsonschema~=4.17.3",
    "rich~=13.5.2",
    "cffi~=1.15.1",
    "Pillow~=10.0.1",
    "sounddevice~=0.4.6",
    "requests~=2.31.0",
    "pyperclip~=1.8.2"
]

modules_win = [
    "pywin32>=306",
    "psutil~=5.9.5"
]


def install(packages: list):
    for package in packages:
        print(f"\nInstalling package: {package}...")
        pip.main(["install", package, "--disable-pip-version-check"])


try:
    install(modules_all)

    match platform.system():
        case "Windows":
            import os
            import atexit
            import psutil

            atexit.register(lambda: psutil.Process(os.getppid()).name() == "py.exe" and input("Press enter to exit..."))
            install(modules_win)
            libmgba_url = (
                f"https://github.com/hanzi/libmgba-py/releases/download/{libmgba_tag}/"
                f"libmgba-py_{libmgba_ver}_win64.zip"
            )

        case "Linux":
            linux_release = platform.freedesktop_os_release()
            if not (linux_release["ID"] == "ubuntu" and linux_release["VERSION_ID"] == "23.04") or not (
                linux_release["ID"] == "debian" and linux_release["VERSION_ID"] == "12"
            ):
                print(
                    f'You are running an untested version of Linux ({linux_release["PRETTY_NAME"]}). '
                    "Currently, only Ubuntu 23.04 and Debian 12 have been tested and confirmed working."
                )
                input("Press enter to install libmgba anyway...")
            libmgba_url = (
                f"https://github.com/hanzi/libmgba-py/releases/download/{libmgba_tag}/"
                f"libmgba-py_{libmgba_ver}_ubuntu-lunar.zip"
            )

        case _:
            raise Exception(f"{platform.system()} is unsupported, currently, only Windows and Linux are supported.")

    if platform.architecture()[0] != "64bit":
        raise Exception(
            f"{platform.architecture()[0]} architecture is currently unsupported, "
            "only 64-bit architecture is supported by this bot!"
        )

    this_directory = pathlib.Path(__file__).parent
    libmgba_directory = this_directory / "mgba"
    if not libmgba_directory.exists():
        print(f"Downloading libmgba from `{libmgba_url}`...")
        import requests

        response = requests.get(libmgba_url)
        if response.status_code == 200:
            print("Unzipping libmgba into `./mgba`...")
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_handle:
                zip_handle.extractall(this_directory)

except Exception as e:
    print(str(e), file=sys.stderr)
