import io
import pathlib
import platform
import subprocess
import sys
import zipfile

libmgba_tag = '0.2.0-2'
libmgba_ver = '0.2.0'

try:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', './requirements.txt'])

    match platform.system():
        case 'Windows':
            import os
            import atexit
            import psutil

            atexit.register(lambda: psutil.Process(os.getppid()).name() == 'py.exe' and input('Press enter to exit...'))
            libmgba_url = f'https://github.com/hanzi/libmgba-py/releases/download/{libmgba_tag}/'\
                          f'libmgba-py_{libmgba_ver}_win64.zip'

        case 'Linux':
            linux_release = platform.freedesktop_os_release()
            if linux_release['ID'] == 'ubuntu' and linux_release['VERSION_ID'] == '23.04':
                print("You are running Ubuntu 23.04.")
            elif linux_release['ID'] == 'debian' and linux_release['VERSION_ID'] == '12':
                print("You are running Debian 12.")
            else:
                raise Exception('Currently, only Ubuntu 23.04 and Debian 12 are supported by this bot. '
                                f'You are running {linux_release["PRETTY_NAME"]}.')

            libmgba_url = f'https://github.com/hanzi/libmgba-py/releases/download/{libmgba_tag}/'\
                          f'libmgba-py_{libmgba_ver}_ubuntu-lunar.zip'

        case _:
            raise Exception(f'Currently, only Windows, Ubuntu 23.04, and Debian 12 are supported by this bot. '
                            'You are running {platform.system()}!')

    if platform.architecture()[0] != '64bit':
        raise Exception('Only 64-bit systems are supported by this bot!')

    this_directory = pathlib.Path(__file__).parent
    libmgba_directory = this_directory / 'mgba'
    if not libmgba_directory.exists():
        print(f'Downloading libmgba from `{libmgba_url}`...')
        import requests
        response = requests.get(libmgba_url)
        if response.status_code == 200:
            print('Unzipping libmgba into `./mgba`...')
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_handle:
                zip_handle.extractall(this_directory)

except Exception as e:
    print(str(e), file=sys.stderr)
