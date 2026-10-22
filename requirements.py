import platform
import sys

from modules.runtime import get_base_path, is_virtualenv
from modules.version import pokebot_name, pokebot_version

recommended_python_version = "3.14"
supported_python_versions = ["3.11", "3.12", "3.13", "3.14"]

libmgba_tag = "0.2.0-2"
libmgba_ver = "0.2.0"

# This is a list of requirements for `pip`, akin to `requirements.txt`.
required_modules = [
    "confz~=2.1",
    "numpy~=2.4.0",
    "setuptools",
    "ruamel.yaml~=0.19.1",
    "pypresence~=4.6",
    "obsws-python~=1.8",
    "discord-webhook~=1.4",
    "rich~=15.0",
    "cffi~=2.0",
    "Pillow~=12.0",
    "sounddevice~=0.5.0",
    "plyer~=2.1",
    "notify-py~=0.3.43",
    "apispec~=6.10",
    "ttkthemes~=3.3",
    "darkdetect~=0.8.0",
    "show-in-file-manager~=1.1",
    "aiohttp~=3.13",
    "requests~=2.32",
]

if platform.system() == "Windows":
    required_modules.extend(["pywin32>=306", "psutil~=7.2"])


def get_requirements_hash() -> str:
    """
    This is used to check whether (a) the requirements have changed or (b) the system's Python version
    has changed, both of which indicates that we should re-check the requirements.
    :return: A hash of all the current requirements, as well as this system's Python version.
    """
    import hashlib

    requirements_block = "\n".join(
        [
            *required_modules,
            platform.python_version(),
            libmgba_ver,
            libmgba_tag,
            recommended_python_version,
            *supported_python_versions,
        ]
    )
    return hashlib.sha1(requirements_block.encode("utf-8")).hexdigest()


def update_requirements(ask_for_confirmation: bool = True) -> bool:
    """
    This will run `pip install` for all requirements configured above, as well as check that
    `libmgba-py` is present and that the Python environment (version, 64-bit) is compatible.

    It will throw an error _and exit the program_ if an incompatibility is found.

    :param ask_for_confirmation: Whether the user should be asked for confirmation before
                                 installing any packages. This option is here, so we can
                                 install requirements non-interactively in the pyinstaller
                                 build process.
    :return: Whether updating the requirements succeeded.
    """
    python_version_tuple = platform.python_version_tuple()
    python_version = f"{str(python_version_tuple[0])}.{str(python_version_tuple[1])}"
    if python_version not in supported_python_versions:
        supported_versions_list = ", ".join(supported_python_versions)

        highest_supported_version = supported_python_versions[-1].split(".")
        if int(python_version_tuple[0]) == int(highest_supported_version[0]) and int(python_version_tuple[1]) > int(
            highest_supported_version[1]
        ):
            print(f"WARNING: The Python version you are using ({platform.python_version()}) is not yet supported.")
            print(f"Supported versions are: {supported_versions_list}\n")
            print("While this version MIGHT work, we have not tested that and so you might experience issues with it.")
            print(f"It is recommended that you install Python {recommended_python_version}.\n")

            response = input(
                "Do you want to risk it and proceed anyway? (Please do not ask for support if you do.) [y/N] "
            )
            print("")
            if response.lower() != "y":
                print("Not proceeding with this version of Python.")
                sys.exit(1)
        else:
            print(f"ERROR: The Python version you are using (Python {platform.python_version()}) is not supported.\n")
            print(f"Supported versions are: {supported_versions_list}")
            print(f"It is recommended that you install Python {recommended_python_version}.")
            sys.exit(1)

    # Some dependencies only work with 64-bit Python. Since this isn't the 90s anymore,
    # we'll just require that.
    if platform.architecture()[0] != "64bit":
        print(f"ERROR: A 64-bit version of Python is required in order to run {pokebot_name} {pokebot_version}.\n")
        print(f"You are currently running a {platform.architecture()[0]} version.")
        sys.exit(1)

    # To avoid surprising the user by installing packages in the global Python environment,
    # we ask for confirmation first. This is skipped if we're inside a virtualenv.
    if ask_for_confirmation and not is_virtualenv():
        print(f"The following Python modules need to be checked and possibly installed:\n")
        for module in required_modules:
            print(f"  * {module}")
        print("")
        response = input("Install those modules? [y/N] ")
        print("")
        if response.lower() != "y":
            print("Not installing any requirements -- the bot might not work this way!")
            return False

    # Run `pip install` on all required modules.
    import subprocess

    pip_flags = ["--disable-pip-version-check", "--no-python-version-warning"]
    if not is_virtualenv():
        pip_flags.append("--user")

    for module in required_modules:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", *pip_flags, module],
            stderr=sys.stderr,
            stdout=sys.stdout,
        )

    # Make sure that `libmgba-py` is installed.
    print("")
    libmgba_directory = get_base_path() / "mgba"
    if not libmgba_directory.is_dir():
        match platform.system():
            case "Windows":
                libmgba_url = (
                    f"https://github.com/hanzi/libmgba-py/releases/download/{libmgba_tag}/"
                    f"libmgba-py_{libmgba_ver}_win64.zip"
                )

            case "Linux":
                linux_release = platform.freedesktop_os_release()
                if "VERSION_ID" not in linux_release:
                    linux_release["VERSION_ID"] = "none"
                supported_linux_releases = [
                    ("ubuntu", "23.04"),
                    ("ubuntu", "23.10"),
                    ("ubuntu", "24.04"),
                    ("ubuntu", "26.04"),
                    ("debian", "12"),
                    ("debian", "13"),
                    ("pop", "22.04"),
                    ("arch", "none"),
                ]
                if (
                    linux_release["ID"],
                    linux_release["VERSION_ID"],
                ) not in supported_linux_releases:
                    print(
                        f'You are running an untested version of Linux ({linux_release["PRETTY_NAME"]}). '
                        f"Currently, only {supported_linux_releases} have been tested and confirmed working."
                    )
                    input("Press enter to install libmgba-py anyway...")
                libmgba_url = (
                    f"https://github.com/hanzi/libmgba-py/releases/download/{libmgba_tag}/"
                    f"libmgba-py_{libmgba_ver}_ubuntu-lunar.zip"
                )

            case "Darwin":
                if platform.machine() == "arm64":
                    # ARM-based Macs
                    libmgba_url = (
                        f"https://github.com/hanzi/libmgba-py/releases/download/{libmgba_tag}/"
                        f"libmgba-py_{libmgba_ver}_macos-arm64.zip"
                    )
                else:
                    # Intel-based Macs
                    libmgba_url = (
                        f"https://github.com/hanzi/libmgba-py/releases/download/{libmgba_tag}/"
                        f"libmgba-py_{libmgba_ver}_macos-x86_64.zip"
                    )

            case _:
                print(
                    f"ERROR: {platform.system()} is unsupported. "
                    "Only Windows, Linux, and MacOS are currently supported."
                )
                sys.exit(1)

        import io
        import requests
        import zipfile

        response = requests.get(libmgba_url)
        if response.status_code == 200:
            print("Unzipping libmgba into `./mgba`...")
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_handle:
                zip_handle.extractall(get_base_path())
        else:
            print(f"ERROR: Could not download libmgba-py ({libmgba_url})")
            sys.exit(1)

    _check_tkinter()

    # Mark the requirements for the current bot version as checked, so we do not
    # have to run all of this again until the next update.
    with open(get_base_path() / ".last-requirements-check", "w") as file:
        file.write(get_requirements_hash())

    print("")

    return True


def _get_tkinter_install_hint() -> str:
    """
    :return: Instructions on how to install Tk for the Python installation that is currently running.
    """
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

    match platform.system():
        case "Windows":
            return "Run the Python installer again, choose 'Modify' and make sure that 'tcl/tk and IDLE' is ticked."

        case "Darwin":
            if sys.base_prefix.startswith(("/opt/homebrew", "/usr/local")):
                return f"Install it with Homebrew: brew install python-tk@{python_version}"
            return "Install Python using the installer from https://www.python.org/, which includes Tk."

        case "Linux":
            # Distribution packages only help if this is the distribution's own Python and not,
            # say, one that has been built by pyenv.
            if sys.base_prefix != "/usr":
                return (
                    "This Python installation has been built without Tk support. Install your "
                    "distribution's Tk development package (e.g. `tk-dev`) and then reinstall this Python."
                )

            try:
                linux_release = platform.freedesktop_os_release()
            except OSError:
                linux_release = {}
            distribution_ids = {linux_release.get("ID", ""), *linux_release.get("ID_LIKE", "").split()}

            if distribution_ids & {"debian", "ubuntu"}:
                return (
                    "Install it with: sudo apt install python3-tk\n"
                    f"  (If this is not your distribution's default Python, e.g. one from the deadsnakes "
                    f"PPA, the package is called python{python_version}-tk instead.)"
                )
            elif distribution_ids & {"fedora", "rhel", "centos"}:
                return "Install it with: sudo dnf install python3-tkinter"
            elif "arch" in distribution_ids:
                return "Install it with: sudo pacman -S tk"
            elif distribution_ids & {"suse", "opensuse"}:
                return "Install it with: sudo zypper install python3-tk"
            elif "alpine" in distribution_ids:
                return "Install it with: sudo apk add python3-tkinter"

    return "Install your distribution's Tk package for Python (usually called `python3-tk` or `python3-tkinter`)."


def _check_tkinter() -> None:
    # Tk cannot be installed with `pip`, so all we can do is tell the user how to get it
    # if it is missing.
    try:
        import tkinter
    except ImportError as error:
        print(f"WARNING: Tk is not available in this Python installation ({error}).")
        print("The GUI needs it, but we cannot install it for you.")
        print(f"  {_get_tkinter_install_hint()}")
        print("Alternatively, you can run the bot without a GUI using `--headless`.\n")


def check_requirements() -> bool:
    """
    Checks whether the dependencies of this app are up-to-date, and if necessary runs
    `update_requirements()` to fetch them.

    :return: Whether requirements are up-to-date.
    """

    # We do not want to do download requirements every single time the bot is started.
    # As a quick sanity check, we store the current bot version in `.last-requirements-check`.
    # If that file is present and contains the current bot version, we skip the check.
    requirements_file = get_base_path() / ".last-requirements-check"
    requirements_hash = get_requirements_hash()
    if requirements_file.is_file():
        with open(requirements_file, "r") as file:
            if file.read() != requirements_hash:
                print(
                    f"This is a newer version of {pokebot_name} than you have run before, "
                    f"or you have updated your Python version.\n"
                    f"We will have to check again if all requirements are met."
                )
                print("")
                return update_requirements()
    else:
        print(
            f"Seems like this is the first time you are running {pokebot_name}!\n"
            "We will check if your system meets all the requirements to run it."
        )
        print("")
        return update_requirements()


if __name__ == "__main__":
    update_requirements()
