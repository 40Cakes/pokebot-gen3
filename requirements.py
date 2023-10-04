import io
import pathlib
import platform
import requests
import subprocess
import sys
import zipfile

if platform.system() == 'Windows':
    import atexit, os, psutil

    atexit.register(lambda: psutil.Process(os.getppid()).name() == 'py.exe' and input('Press enter to exit...'))

    libmgba_url = 'https://github.com/hanzi/libmgba-py/releases/download/0.2.0-2/libmgba-py_0.2.0_win64.zip'
elif platform.system() == 'Linux':
    linux_release = platform.freedesktop_os_release()
    if linux_release['ID'] != 'ubuntu' or linux_release['VERSION_ID'] != '23.04':
        print(
            'Currently, only Ubuntu 23.04 is supported by this bot. You are running ' + linux_release['PRETTY_NAME'],
            file=sys.stderr
        )
        sys.exit(1)
    libmgba_url = 'https://github.com/hanzi/libmgba-py/releases/download/0.2.0-2/libmgba-py_0.2.0_ubuntu-lunar.zip'
else:
    print(
        'Currently, only Windows and Ubuntu 23.04 are supported by this bot. You are running ' + platform.system(),
        file=sys.stderr
    )
    sys.exit(1)

if platform.architecture()[0] != '64bit':
    print('Only 64-bit systems are supported by this bot.', file=sys.stderr)
    sys.exit(1)

try:
    this_directory = pathlib.Path(__file__).parent
    libmgba_directory = this_directory / 'mgba'
    if not libmgba_directory.exists():
        response = requests.get(libmgba_url)
        if response.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_handle:
                zip_handle.extractall(this_directory)

    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', './requirements.txt'])
except Exception as e:
    print(str(e), file=sys.stderr)
