# pyelftools
from elftools.dwarf.dwarfinfo import DWARFInfo
from elftools.elf.elffile import ELFFile
from pipa.common.logger import logger
from pipa.common.utils import (
    tar,
    process_compression,
    FileFormat,
    check_file_format,
)
from pipa.parser.perf_buildid import PerfBuildidData
from pipa.common.cmd import run_command
from pipa.service.call_graph.addr import DEFAULT_BUILD_ID_DIR
from typing import List, Dict
from tempfile import mktemp, mkdtemp
import os


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


def archive(
    perf_data: str,
    output_path: str,
    replace_modules: Dict[str, str] = {},
):
    """PIPA Archive

    archive buildid and source files in a perf data

    Args:
        perf_data (str): perf data
        output_path (str): stored archive to output path
        replace_modules (Dict[str, str]): replace some modules' to specified one, useful when original module doesn't provide debuginfo at all. For example, '/path/to/workload/cmd' -> '/path/to/workload-debug/cmd', just pass replace_modules={'/path/to/workload/cmd': '/path/to/workload-debug/cmd'}
    """
    if not os.path.exists(perf_data):
        logger.error(f"perf data {perf_data} not exists!")
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
    logger.debug("Get original buildid list:")
    for bid in f"{perf_buildid_data.to_raw_dataframe()}".splitlines():
        logger.debug(bid)
    modules_list = perf_buildid_data.get_modules()
    # apply module replace
    for i in range(len(modules_list)):
        for o, v in replace_modules.items():
            m = modules_list[i]
            if m != o:
                continue
            modules_list[i] = v
    logger.debug("Final module list:")
    for i, m in enumerate(modules_list):
        logger.debug(f"{i}: {m}")
    source_files = []
    for module in modules_list:
        if not os.path.exists(module):
            logger.warning(f"Not found ELF File {module} in buildid list")
            continue
        # check if it's an elf file with debuginfo
        # if it's a compress file, extract to a tmpdir and will use the extracted elf file (if it contains) for further processing
        # if it's not a compress file or elf file, pass
        fformat = check_file_format(module)
        if fformat == FileFormat.xz:
            # buildid will generate a xz compressed file named like drm_vram_helper.ko.xz
            # it contains debuginfo elf, named like drm_vram_helper.ko
            tmpd = mkdtemp()
            extracted, _ = os.path.splitext(os.path.basename(module))
            extracted = os.path.join(tmpd, extracted)
            process_compression(
                compressed=module,
                decompressed=extracted,
                format=FileFormat.xz,
                decompress=True,
            )
            if not os.path.exists(extracted):
                logger.warning(
                    f"Extract {module} to {tmpd}, but expected elf file {extracted} not found"
                )
                continue
            module = extracted
        elif fformat != FileFormat.elf:
            continue
        # open elf file
        f = open(module, "rb")
        elffile = ELFFile(f)
        if not elffile.has_dwarf_info():
            logger.warning(f"{module} has no dwarf info, please provide debuginfo")
            f.close()
            continue
        # get dwarf info
        dwarfinfo = elffile.get_dwarf_info()
        if not dwarfinfo.has_debug_info:
            logger.warning(
                f"{module}'s dwarf lost debuginfo, check your compile methods"
            )
            continue
        source_files.extend(find_all_source_files(dwarfinfo=dwarfinfo))
        f.close()
    # get archive manifest
    archive_files = get_archive_manifest(perf_buildid_data)
    # generate archive
    buildid_tar = os.path.join(output_path, f"{perf_data}.buildid.tar")
    buildid_bz2 = f"{buildid_tar}.bz2"
    sourcefiles_tar = os.path.join(output_path, f"{perf_data}.sourcefiles.tar")
    sourcefiles_bz2 = f"{sourcefiles_tar}.bz2"
    tar(
        output_tar=buildid_tar,
        base_dir=DEFAULT_BUILD_ID_DIR,
        manifest=archive_files,
    )
    process_compression(
        decompressed=buildid_tar,
        compressed=buildid_bz2,
        format=FileFormat.bzip2,
        decompress=False,
    )
    tar(output_tar=sourcefiles_tar, manifest=source_files)
    process_compression(
        decompressed=sourcefiles_tar,
        compressed=sourcefiles_bz2,
        format=FileFormat.bzip2,
        decompress=False,
    )
    print(f"Created buildid archive: {buildid_bz2}")
    print(f"Created sourcefiles archive: {sourcefiles_bz2}")
    print("Now you can transfer them to another machine")
    print("Usage:")
    print(f"\t tar -xf {os.path.basename(buildid_bz2)} -C ~/.debug")
    print(f"\t tar -xf {os.path.basename(sourcefiles_bz2)} -C /")
    print("\t\t Or")
    print(
        f"\t tar -xf {os.path.basename(sourcefiles_bz2)} -C /path/to/source_file_prefix"
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
