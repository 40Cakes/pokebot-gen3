import os
from modules.console import console


def read_file(file: str) -> str:
    """
    Simple function to read data from a file, return False if file doesn't exist
    :param file: File to read
    :return: File's contents (str)
    """
    try:
        if os.path.exists(file):
            with open(file, mode="r", encoding="utf-8") as open_file:
                return open_file.read()
        else:
            return None
    except:
        console.print_exception(show_locals=True)()
        return None


def write_file(file: str, value: str, mode: str = "w") -> bool:
    """
    Simple function to write data to a file, will create the file if doesn't exist.
    Writes to a temp file, then performs os.remove + os.rename to prevent corruption of files (atomic operations).

    :param file: File to write to
    :param value: Value to write to file
    :param mode: Write mode
    :return: True if file was written to successfully, otherwise False (bool)
    """
    try:
        tmp_file = file + ".tmp"
        directory = os.path.dirname(tmp_file)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(tmp_file, mode=mode, encoding="utf-8") as save_file:
            save_file.write(value)
        if os.path.exists(file):
            os.remove(file)
        os.rename(tmp_file, file)
        return True
    except:
        console.print_exception(show_locals=True)()
        return False


def write_pk(file: str, data: bytes) -> bool:
    """
    Slightly modified funciton to the write_file function that provides the ability
    to write byte arrays out directly into a file

    :param file: File to write to
    :param data: Pokemon data to be written
    :return: True if file was written to successfully, otherwise False (bool)
    """
    try:
        # Remove file if it already exists
        if os.path.exists(file):
            os.remove(file)

        # Create the directory if required
        directory = os.path.dirname(file)
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Open the file and write the data
        with open(file, "wb") as binary_file:
            binary_file.write(data)
        return True
    except:
        console.print_exception(show_locals=True)
        return False
