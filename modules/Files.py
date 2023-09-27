import os
import shutil
from typing import NoReturn
from modules.Console import console

def ReadFile(file: str) -> str:
    """
    Simple function to read data from a file, return False if file doesn't exist
    :param file: File to read
    :return: File's contents (str)
    """
    try:
        if os.path.exists(file):
            with open(file, mode='r', encoding='utf-8') as open_file:
                return open_file.read()
        else:
            return None
    except:
        console.print_exception(show_locals=True)()
        return None


def WriteFile(file: str, value: str, mode: str = 'w') -> bool:
    """
    Simple function to write data to a file, will create the file if doesn't exist.
    Writes to a temp file, then performs os.remove + os.rename to prevent corruption of files (atomic operations).

    :param file: File to write to
    :param value: Value to write to file
    :param mode: Write mode
    :return: True if file was written to successfully, otherwise False (bool)
    """
    try:
        tmp_file = file + '.tmp'
        directory = os.path.dirname(tmp_file)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(tmp_file, mode=mode, encoding='utf-8') as save_file:
            save_file.write(value)
        if os.path.exists(file):
            os.remove(file)
        os.rename(tmp_file, file)
        return True
    except:
        console.print_exception(show_locals=True)()
        return False


def BackupFolder(source, destination) -> NoReturn:
    """
    Backup a folder, .zip up a source directory and write file to destination.

    :param source: path to backup
    :param destination: path to write .zip backup file
    :return:
    """
    basename = os.path.basename(destination)
    dst_dir = os.path.dirname(destination)
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    name = basename.split('.')[0]
    format = basename.split('.')[1]
    shutil.make_archive(name, format, os.path.dirname(source), os.path.basename(source.strip(os.sep)))
    shutil.move('%s.%s' % (name, format), destination)
