# pyelftools
from elftools.dwarf.dwarfinfo import DWARFInfo
from elftools.elf.elffile import ELFFile
from pipa.common.logger import logger
from pipa.parser.perf_buildid import PerfBuildidData
from pipa.common.cmd import run_command
from pipa.service.call_graph.addr import DEFAULT_BUILD_ID_DIR
from typing import List, Optional
from tempfile import mktemp
import os
import tarfile


def find_all_source_files(dwarfinfo: DWARFInfo) -> List[str]:
    source_files = []
    # Iter all Compile Units, may be a source file or part of it.
    for CU in dwarfinfo.iter_CUs():
        # get the compile unit's line program (includes mapping from machine codes to souce codes)
        lineprog = dwarfinfo.line_program_for_CU(CU)
        if lineprog is None:
            continue
        top_die = CU.get_top_DIE()
        comp_dir = top_die.attributes.get("DW_AT_comp_dir")
        relative_dir: str = ""
        if comp_dir:
            if type(comp_dir) is str:
                relative_dir = comp_dir
            else:
                relative_dir = comp_dir.value.decode("utf-8")  # type: ignore
        delta = 1 if lineprog.header.version < 5 else 0

        for file_entry in lineprog["file_entry"]:
            file_name = file_entry.name.decode("utf-8")
            dir_index = file_entry.dir_index
            try:
                dir_name = lineprog["include_directory"][dir_index - delta].decode(
                    "utf-8"
                )
            except IndexError:
                dir_name = ""
            file_name = os.path.join(dir_name, file_name)
            if not os.path.exists(file_name):
                d = os.path.join(relative_dir, file_name)
                if not os.path.exists(d):
                    logger.warning(f"source file {d} couldn't found, please check")
                    continue
                else:
                    file_name = d
            realpath = os.path.realpath(file_name)
            source_files.append(realpath)
            if os.path.islink(file_name):
                abspath = os.path.abspath(file_name)
                if abspath != realpath:
                    source_files.append(abspath)
    return source_files


def get_archive_manifest(
    builid_data: PerfBuildidData, perf_buildid_dir=DEFAULT_BUILD_ID_DIR
) -> List[str]:
    manifest = []
    if not os.path.exists(perf_buildid_dir):
        logger.error(f"perf buildid dir {perf_buildid_dir} not exists!")
        return []
    perf_buildid_linkdir = os.path.realpath(perf_buildid_dir)
    for build_id in builid_data.buildid_lists.values():
        linkname = f".build-id/{build_id[0:2]}/{build_id[2:]}"
        linkfile = os.path.join(perf_buildid_dir, linkname)
        realfile = os.path.realpath(linkfile)
        manifest.append(linkname)
        manifest.append(os.path.relpath(realfile, perf_buildid_linkdir))
    return manifest


def create_tar_bz2(output_tar, manifest: List[str], base_dir: Optional[str] = None):
    """
    Create a tar.bz2 archive based on a manifest file.

    Args:
        output_tar (str): Path to the output tar.bz2 file.
        base_dir (str): Base directory to use for relative paths.
        manifest_file (str): Path to the manifest file containing files to include.
    """
    with tarfile.open(output_tar, mode="w:bz2") as tar:
        for file in manifest:
            full_path = file
            if base_dir:
                full_path = os.path.join(base_dir, full_path)
            if os.path.exists(full_path):
                # Add file to tar archive
                tar.add(full_path, arcname=file)
            else:
                logger.warning(
                    f"Warning: {full_path} does not exist and will be skipped."
                )
                continue


def archive(perf_data: str, output_path: str):
    if not os.path.exists(perf_data):
        logger.error(f"{perf_data} not exists!")
        return
    if not os.path.exists(output_path):
        os.makedirs(output_path)
        logger.warning(f"{output_path} not exists, created")
    perf_buildid = mktemp()
    run_command(
        f"perf buildid-list -i {perf_data} --with-hits | grep -v '^ ' > {perf_buildid}"
    )
    # get source files' locations
    perf_buildid_data = PerfBuildidData.from_file(perf_buildid)
    if len(perf_buildid_data.buildid_lists) == 0:
        logger.error("No buildid found in perf data")
        return
    source_files = []
    for module in perf_buildid_data.buildid_lists.keys():
        if not os.path.exists(module):
            logger.warning(f"Not found ELF File {module}")
            continue
        f = open(module, "rb")
        # open elf file
        elffile = ELFFile(f)
        if not elffile.has_dwarf_info():
            logger.warning(f"{module} has no dwarf info, please provide debuginfo")
            f.close()
            continue
        # get dwarf info
        dwarfinfo = elffile.get_dwarf_info()
        source_files.extend(find_all_source_files(dwarfinfo=dwarfinfo))
        f.close()
    # get archive manifest
    archive_files = get_archive_manifest(perf_buildid_data)
    # generate archive
    buildid_tar = os.path.join(output_path, f"{perf_data}.buildid.tar.bz2")
    sourcefiles_tar = os.path.join(output_path, f"{perf_data}.sourcefiles.tar.bz2")
    create_tar_bz2(
        output_tar=buildid_tar,
        base_dir=DEFAULT_BUILD_ID_DIR,
        manifest=archive_files,
    )
    create_tar_bz2(
        output_tar=sourcefiles_tar,
        manifest=source_files,
    )
    print(f"Created buildid archive: {buildid_tar}")
    print(f"Created sourcefiles archive: {sourcefiles_tar}")
    print("Now you can transfer them to another machine")
    print("Usage:")
    print(f"\t tar -xf {os.path.basename(buildid_tar)} -C ~/.debug")
    print(f"\t tar -xf {os.path.basename(sourcefiles_tar)} -C /")
    print("\t\t Or")
    print(
        f"\t tar -xf {os.path.basename(sourcefiles_tar)} -C /path/to/source_file_prefix"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Archive buildid and source files")
    parser.add_argument(
        "-i", "--perf-data", default="perf.data", help="Path to the perf data"
    )
    parser.add_argument("-o", "--output-path", default="./", help="Set output path")
    args = parser.parse_args()
    perf_data = args.perf_data
    output_path = args.output_path
