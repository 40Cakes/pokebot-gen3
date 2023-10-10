import io
import pathlib
import platform
import subprocess
import sys
import zipfile

libmgba_tag = "0.2.0-2"
libmgba_ver = "0.2.0"

try:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "./requirements.txt"])

    match platform.system():
        case "Windows":
            import os
            import atexit
            import psutil

            atexit.register(lambda: psutil.Process(os.getppid()).name() == "py.exe" and input("Press enter to exit..."))
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
