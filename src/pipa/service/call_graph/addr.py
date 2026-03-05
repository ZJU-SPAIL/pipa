from typing import Dict, List, Optional, Tuple

import os
import time

from pipa.common.logger import logger
from pipa.common.utils import find_closest_factor_pair

# multi processing
from multiprocessing.pool import Pool as PoolCls

# pyelftools
from elftools.dwarf.dwarfinfo import DWARFInfo
from elftools.elf.elffile import ELFFile
from elftools.dwarf.lineprogram import LineState, LineProgram
from elftools.elf.sections import SymbolTableSection

# capstone for disassemble
from capstone import Cs
from capstone import (
    CS_ARCH_ARM,
    CS_ARCH_ARM64,
    CS_MODE_32,
    CS_MODE_ARM,
    CS_MODE_V8,
    CS_ARCH_X86,
    CS_MODE_64,
    CS_ARCH_PPC,
)

DEFAULT_BUILD_ID_DIR = os.path.join(os.path.expanduser("~"), ".debug")
"""Default build-id dir"""

ADDR2LINE_OPT_STRENGTH = 1e9
"""Operation strength to indicate when to parallelize in addr2line"""


def get_arch_mode(elffile: ELFFile) -> Tuple[int, int]:
    """Judge arch and mode based on elf file

    Args:
        elffile (ELFFile): The elf file

    Raises:
        NotImplementedError: Will raise error when the arch is not supported

    Returns:
        Tuple[int, int]: (arch, mode)
    """
    arch = elffile["e_machine"]
    elf_header = elffile["e_ident"]

    if arch == "EM_X86_64":
        return (CS_ARCH_X86, CS_MODE_64)
    elif arch == "EM_386":
        return (CS_ARCH_X86, CS_MODE_32)
    elif arch == "EM_ARM":
        a = CS_ARCH_ARM
        if elf_header["EI_CLASS"] == "ELFCLASS32":
            return (a, CS_MODE_ARM)
        else:
            return (a, CS_MODE_ARM | CS_MODE_V8)
    elif arch == "EM_AARCH64":
        return (CS_ARCH_ARM64, CS_MODE_ARM)
    elif arch == "EM_PPC64":
        return (CS_ARCH_PPC, CS_MODE_64)
    else:
        raise NotImplementedError(
            f"Unsupported architecture. Arch: {arch} / ELF Header: {elf_header}"
        )


def get_symbol_addresses(
    elffile: ELFFile, func_name: Optional[str]
) -> Dict[str, Tuple[int, int]]:
    """Find all functions' name / start address / size in the given elf file

    Args:
        elffile (ELFFile): The elf file
        func_name (Optional[str]): If given, will only return the given function's info, otherwise return all functions' info

    Returns:
        tuple[str, Tuple[int, int]]: Take function's name as key, start address and size as value in tuple format: (start address, size)
    """
    symbol_addresses = {}
    for section in elffile.iter_sections():
        if not isinstance(section, SymbolTableSection):
            continue
        for symbol in section.iter_symbols():
            # function type
            if symbol["st_info"]["type"] == "STT_FUNC":
                name = symbol.name
                addr = symbol["st_value"]  # start address
                size = symbol["st_size"]  # function size
                if func_name is None or func_name == name:
                    symbol_addresses[name] = (addr, size)
    return symbol_addresses


def get_text_section(elffile: ELFFile) -> Tuple[bytes, int]:
    """Get data and start addr of text section in the elf file

    Args:
        elffile (ELFFile): The elf file

    Raises:
        ValueError: Not found `.text` section in the elf file

    Returns:
        Tuple[bytes, int]: (section data, section start address)
    """
    text_section = elffile.get_section_by_name(".text")
    if not text_section:
        raise ValueError("Not found .text section in the elf file")
    return text_section.data(), text_section["sh_addr"]


def disassemble_func(
    elfcodes: bytes, start_addr: int, arch: int, mode: int
) -> Dict[int, Tuple[str, str]]:
    """Disassemble function

    Args:
        elfcodes (bytes): The elf codes
        start_addr (int): Start address of assemble codes
        arch (int): The elf arch
        mode (int): The elf mode

    Returns:
        Dict[int, Tuple[str, str]]: The disassembled function, key is address, value is (mnemonic, op_str)
    """
    md = Cs(arch, mode)
    md.detail = False
    md.skipdata = True
    func_asm = {}
    for i in md.disasm(elfcodes, start_addr):
        # mnemonic indicates the instruction
        # op_str indicates the operands
        func_asm[i.address] = (i.mnemonic, i.op_str)
    return func_asm


def addr2lines(
    dwarfinfo: DWARFInfo,
    addresses: List[int],
    pool: PoolCls,
) -> List[Tuple[str, int, int, int, str]]:
    """Address to source line mapping

    Args:
        dwarfinfo (DWARFInfo): DWARFInfo
        addresses (List[int]): addresses to map
        pool (PoolCls): multiprocessing pool

    Returns:
        List[Tuple[str, int, int, int]]: The source line mapping, list of (file_name, address, line, column)

    Example:
    >>> import pipa.service.call_graph.addr as pipa_cfg
    >>> pipa_cfg.ADDR2LINE_OPT_STRENGTH = 2e8
    >>> dwarfinfo = DWARFInfo(elf)
    >>> with Pool(NUM_CORES_PHYSICAL) as pool:
    >>>     addr2lines(dwarfinfo, [0x400000, 0x400001], pool)
    [('main.c', 0x400000, 1, 1), ('main.c', 0x400001, 1, 2)]
    """
    operations_strength = ADDR2LINE_OPT_STRENGTH
    parallel = pool._processes  # type: ignore
    sourcelines: List[Tuple[str, int, int, int, str]] = []
    state_list: List[Tuple[int, LineState, LineState]] = []
    lineprog_list: List[Tuple[LineProgram, int, str]] = []
    address_len = len(addresses)
    if address_len <= 0:
        return sourcelines
    # Iter all Compile Units, may be a source file or part of it.
    for i, CU in enumerate(dwarfinfo.iter_CUs()):
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
        lineprog_list.append((lineprog, delta, relative_dir))
        prevstate = None

        # Iter all entries in the line program
        entries = lineprog.get_entries()
        for entry in entries:
            state = entry.state
            if state is None:
                continue
            if prevstate is not None and prevstate.address < state.address:
                state_list.append((i, prevstate, state))
            if state.end_sequence:
                prevstate = None
            else:
                prevstate = state
    # prepare for addr2line
    found_addresses = []
    state_len = len(state_list)
    operations_len = address_len * state_len
    logger.debug(f"\t addresses length: {address_len}")
    logger.debug(f"\t state tuple length: {state_len}")
    if operations_len < operations_strength:
        # sequential addr2line
        for state_tuple in state_list:
            for address in addresses:
                # Found address
                lineprog_index, prevstate, state = state_tuple
                lineprog, delta, relative_dir = lineprog_list[lineprog_index]
                # find nearest symbol
                if prevstate.address <= address < state.address:
                    file_entry = lineprog["file_entry"][prevstate.file - delta]
                    file_name = file_entry.name.decode("utf-8")
                    dir_index = file_entry.dir_index
                    try:
                        dir_name = lineprog["include_directory"][
                            dir_index - delta
                        ].decode("utf-8")
                    except IndexError as e:
                        logger.warning("\t Could not found dir name:")
                        logger.warning(f"\t\t address: {address}")
                        logger.warning(f"\t\t dir_index: {dir_index}")
                        logger.warning(f"\t\t delta: {delta}")
                        logger.warning(f"\t\t file_name: {file_name}")
                        logger.warning(f"\t\t line: {prevstate.line}")
                        logger.warning(f"\t\t column: {prevstate.column}")
                        dir_name = ""
                    file_name = os.path.join(dir_name, file_name)
                    sourcelines.append(
                        (
                            file_name,
                            address,
                            prevstate.line,
                            prevstate.column,
                            relative_dir,
                        )
                    )
                    found_addresses.append(address)
                    address_len -= 1
                if address_len <= 0:
                    return sourcelines
    else:
        logger.debug(
            f"\t {operations_len} >= {operations_strength}, will use parallel {parallel} processes to addr2line"
        )

        # allocate tasks
        stime = time.perf_counter()
        m, n = find_closest_factor_pair(parallel)
        state_p = [int(state_len / m)] * m
        for i in range(0, state_len % m):
            state_p[i] += 1
        address_p = [int(address_len / n)] * n
        for i in range(0, address_len % n):
            address_p[i] += 1
        allocate_task = []
        spi = 0
        for sp in state_p:
            api = 0
            for ap in address_p:
                allocate_task.append(
                    (state_list[spi : spi + sp], addresses[api : api + ap])
                )
                api += ap
            spi += sp
        assert len(allocate_task) == parallel
        etime = time.perf_counter()
        logger.debug(f"\t allocate tasks within {etime - stime} seconds")

        # process
        stime = time.perf_counter()
        results = pool.map(addr2l, allocate_task)
        etime = time.perf_counter()
        logger.debug(f"\t perform tasks within {etime - stime} seconds")

        # parse results
        for r in results:
            for rs in r:
                lp_index, addr, pvstate = rs
                lineprog, delta, relative_dir = lineprog_list[lp_index]
                file_entry = lineprog["file_entry"][pvstate.file - delta]
                file_name = file_entry.name.decode("utf-8")
                dir_index = file_entry.dir_index
                try:
                    dir_name = lineprog["include_directory"][dir_index - delta].decode(
                        "utf-8"
                    )
                except IndexError as e:
                    logger.warning("\t Could not found dir name:")
                    logger.warning(f"\t\t address: {addr}")
                    logger.warning(f"\t\t dir_index: {dir_index}")
                    logger.warning(f"\t\t delta: {delta}")
                    logger.warning(f"\t\t file_name: {file_name}")
                    logger.warning(f"\t\t line: {pvstate.line}")
                    logger.warning(f"\t\t column: {pvstate.column}")
                    dir_name = ""
                file_name = os.path.join(dir_name, file_name)
                sourcelines.append(
                    (file_name, addr, pvstate.line, pvstate.column, relative_dir)
                )
                found_addresses.append(addr)
                address_len -= 1
                if address_len <= 0:
                    return sourcelines
    not_found_addresses = list(filter(lambda x: x not in found_addresses, addresses))
    logger.warning(
        f"\t Not all address found sourcelines mapped: {not_found_addresses}"
    )
    logger.warning(f"\t\t {len(not_found_addresses)} addresses not found")
    logger.warning("\t\t check whether add source file info when compiling")
    return sourcelines


def addr2l(task: Tuple[List[Tuple[int, LineState, LineState]], List[int]]):
    """addr2line parallel worker

    Args:
        task (Tuple[List[Tuple[int, LineState, LineState]], List[int]]): the task to be processed, (state_list, addresses)

    Returns:
        result (List[Tuple[int, int, LineState]]): the result of addr2line
    """
    state_list, addresses = task
    result: List[Tuple[int, int, LineState]] = []
    for state_tuple in state_list:
        for address in addresses:
            # Found address
            lineprog_index, prevstate, state = state_tuple
            # find nearest symbol
            if prevstate.address <= address < state.address:
                result.append((lineprog_index, address, prevstate))
    return result
