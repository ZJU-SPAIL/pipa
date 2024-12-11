from math import sqrt
from typing import Tuple, List, Optional, Set
from rich import print
from pipa.common.logger import logger
from enum import Enum, unique
from functools import partial
import tarfile
import os
import sys
import datetime
import shutil
import lzma
import bz2
import random


@unique
class FileFormat(Enum):
    xz = "xz"
    bzip2 = "bz2"
    elf = "elf"
    tar = "tar"
    other = "other"

    def __str__(self) -> str:
        return self.value


def check_file_format(file: str) -> FileFormat:
    """Check the file format of the given file.

    Args:
        file (str): file to be checked

    Returns:
        file_format: The file format of the given file.
    """
    with open(file, "rb") as f:
        # if omitted, will read until EOF
        # the slice is still valid
        magic = f.read(270)
        if magic[0:4] == b"\x7f\x45\x4c\x46":
            # elf file, 4 bytes
            return FileFormat.elf
        elif magic[0:6] == b"\xFD\x37\x7A\x58\x5A\x00":
            # .xz, 6 bytes
            return FileFormat.xz
        elif magic[0:3] == b"BZh":
            # .bz2, 4 bytes
            return FileFormat.bzip2
        elif magic[257:263] == b"ustar " or magic == b"gnutar":
            return FileFormat.tar
        return FileFormat.other


def tar(
    output_tar,
    manifest: List[str] | str,
    base_dir: Optional[str] = None,
):
    """Create a tar archive based on a manifest list.

    Args:
        output_tar (str): Path to the output tar file.
        base_dir (str): Base directory to use for relative paths.
        manifest_file (str | List[str]): file or files in tar archive.
    """
    with tarfile.open(output_tar, mode="w") as tar:
        if type(manifest) is str:
            manifest = [manifest]
        non_duplicate_lists: Set[Tuple[str, str]] = set()
        for file in manifest:
            full_path = file
            if base_dir:
                full_path = os.path.join(base_dir, full_path)
            if os.path.exists(full_path):
                # First add file to set to prevent duplicate files
                # Duplicate files will significantly increase the size of the tar archive
                non_duplicate_lists.add((full_path, file))
            else:
                logger.warning(
                    f"Warning: {full_path} does not exist and will be skipped."
                )
                continue
        # Add file to tar archive
        for f in non_duplicate_lists:
            full_path, file = f
            tar.add(full_path, arcname=file)


def untar(
    input_tar: str,
    output_dir: str,
):
    """
    Extract a tar archive to the specified directory.

    Args:
        input_tar (str): Path to the input tar file.
        output_dir (str): Directory to extract the files to.
    """
    with tarfile.open(input_tar, mode="r") as tar:
        tar.extractall(path=output_dir)
        logger.debug(f"Extracted {input_tar} to {output_dir}")


def process_compression(
    compressed: str, decompressed: str, format: FileFormat, decompress: bool = False
):
    """Compress or decompress a file based on the specified format.

    If in compress mode, will compress `decompressed` to `compressed`

    If in decompress mode, will decompress `compressed` to `decompressed`

    Args:
        compressed (str): Compressed file
        decompressed (str): Decompressed file
        format (file_format): Format of the compressed file
        decompress (bool, optional): Decompress mode. Defaults to False, which is compress mode.
    """
    if format == FileFormat.xz:
        compress_method = lzma.open
    elif format == FileFormat.bzip2:
        compress_method = bz2.open
    else:
        logger.warning(f"not support {format}'s compress or decompress")
        return
    f_in_f = (
        partial(compress_method, compressed)
        if decompress
        else partial(open, decompressed)
    )
    f_out_f = (
        partial(open, decompressed)
        if decompress
        else partial(compress_method, compressed)
    )
    with f_in_f("rb") as f_in, f_out_f("wb") as f_out:
        shutil.copyfileobj(f_in, f_out)


def find_closest_factor_pair(n: int) -> Tuple[int, int]:
    """
    Find closest factor pair of n

    Args:
        n (int): number to find

    Returns:
        Tuple[int, int]: (small factor A, large factor B), A * B = n
    """
    for i in range(int(sqrt(n)), 0, -1):
        if n % i == 0:
            return (i, n // i)


def get_timestamp():
    """
    Returns the current timestamp in the format "YYYY-MM-DD-HH-MM-SS".

    Returns:
        str: The current timestamp.
    """
    return datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")


def handle_user_cancelled(func):
    """
    Decorator function that handles user cancellation by catching the KeyboardInterrupt exception.

    Args:
        func: The function to be decorated.

    Returns:
        The decorated function.

    Raises:
        None.
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt as e:
            # Print "Cancelled by user" and exit
            print("Cancelled by user")
            sys.exit(0)
        except TypeError as e:
            sys.exit(0)

    return wrapper


def generate_unique_rgb_color(data: List, generate_seed=True) -> Tuple[int, int, int]:
    """
    Generate unique RGB color from data

    Args:
        data (Tuple): Generate rgb from hash of data
        generate_seed (bool, optional): Generate random seed for hash. Defaults to True.

    Returns:
        Tuple[int, int, int]: rgb color, (r, g, b)
    """
    if generate_seed:
        data.append(random.randint(1, 256))
    # generate hash
    data_hash = hash(tuple(data))

    r = (data_hash & 0xFF0000) >> 16
    g = (data_hash & 0x00FF00) >> 8
    b = data_hash & 0x0000FF

    r = r % 256
    g = g % 256
    b = b % 256

    return (r, g, b)
