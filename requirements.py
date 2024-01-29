import platform
import sys

from modules.runtime import is_bundled_app, is_virtualenv, get_base_path
from modules.version import pokebot_name, pokebot_version

recommended_python_version = "3.12"
supported_python_versions = ["3.10", "3.11", "3.12"]

libmgba_tag = "0.2.0-2"
libmgba_ver = "0.2.0"

# This is a list of requirements for `pip`, akin to `requirements.txt`.
required_modules = [
    "confz==2.0.1",
    "numpy~=1.26.1",
    "Flask~=2.3.2",
    "Flask-Cors~=4.0.0",
    "ruamel.yaml~=0.18.2",
    "pypresence~=4.3.0",
    "obsws-python~=1.6.0",
    "pandas~=2.1.1",
    "discord-webhook~=1.2.1",
    "jsonschema~=4.17.3",
    "rich~=13.5.2",
    "cffi~=1.16.0",
    "Pillow~=10.0.1",
    "sounddevice~=0.4.6",
    "requests~=2.31.0",
    "pyperclip3~=0.4.1",
    "plyer~=2.1.0",
    "notify-py~=0.3.42",
    "apispec~=6.3.0",
    "apispec-webframeworks~=0.5.2",
    "flask-swagger-ui~=4.11.1",
    "ttkthemes~=3.2.2",
    "darkdetect~=0.8.0",
]

if platform.system() == "Windows":
    required_modules.extend(["pywin32>=306", "psutil~=5.9.5"])


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
                                 installing any packages. This option is here so we can
                                 install requirements non-interactively in the pyinstaller
                                 build process.
    :return: Whether updating the requirements succeeded.
    """
    python_version_tuple = platform.python_version_tuple()
    python_version = f"{str(python_version_tuple[0])}.{str(python_version_tuple[1])}"
    if python_version not in supported_python_versions:
        supported_versions_list = ", ".join(supported_python_versions)
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
                    ("debian", "12"),
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
                    f"ERROR: {platform.system()} is unsupported. Only Windows, Linux, and MacOS are currently supported."
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

    # Mark the requirements for the current bot version as checked, so we do not
    # have to run all of this again until the next update.
    with open(get_base_path() / ".last-requirements-check", "w") as file:
        file.write(get_requirements_hash())

    print("")

    return True


def check_requirements() -> bool:
    """
    Checks whether the dependencies of this app are up-to-date, and if necessary runs
    `update_requirements()` to fetch them.

    :return: Whether requirements are up-to-date.
    """

    # Never check requirements if we are in a bundle generated by pyinstaller, since all the
    # requirements should already be included. Also, it's not possible to download requirements
    # inside a bundle anyway.
    if is_bundled_app():
        return True

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
