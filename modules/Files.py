import os
import shutil
import logging

log = logging.getLogger(__name__)


def ReadFile(file: str):
    """
    Simple function to read data from a file, return False if file doesn't exist
    :param file: File to read
    :return: File's contents, if found. Otherwise None
    """
    try:
        if os.path.exists(file):
            with open(file, mode='r', encoding='utf-8') as open_file:
                return open_file.read()
        else:
            return None
    except Exception as e:
        log.exception(str(e))
        return None


def WriteFile(file: str, value: str, mode: str = 'w'):
    """
    Simple function to write data to a file, will create the file if doesn't exist
    :param file: File to write to
    :param value: Value to write to file
    :param mode: Write mode
    :return: Boolean value of whether file was written to successfully
    """
    try:
        dirname = os.path.dirname(file)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(file, mode=mode, encoding='utf-8') as save_file:
            save_file.write(value)
            return True
    except Exception as e:
        log.exception(str(e))
        return False

def BackupFolder(source, destination):
    basename = os.path.basename(destination)
    dst_dir = os.path.dirname(destination)
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    name = basename.split('.')[0]
    format = basename.split('.')[1]
    shutil.make_archive(name, format, os.path.dirname(source), os.path.basename(source.strip(os.sep)))
    shutil.move('%s.%s' % (name, format), destination)
