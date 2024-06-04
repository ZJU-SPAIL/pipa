from pipa.common.config import CONFIG_DIR
from pipa.common.cmd import run_command
import shutil
import os


def write_string_to_file(string: str, filename: str, append: bool = False):
    file_path = os.path.join(CONFIG_DIR, filename)
    with open(file_path, "a" if append else "w") as file:
        result = file.write(string)
    return result


def copy_file(source_file: str, destination_folder: str = CONFIG_DIR):
    return shutil.copy(source_file, destination_folder)


def run_command_and_write_to_file(command: str, filename: str, append: bool = False):
    result = run_command(command, log=True)
    write_string_to_file(result, filename, append)
    return result
