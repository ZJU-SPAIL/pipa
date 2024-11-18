from typing import Dict, List, Optional, Tuple

import os
import time

from pipa.common.logger import logger
from pipa.common.hardware.cpu import NUM_CORES_PHYSICAL
from pipa.common.utils import find_closest_factor_pair

# multi processing
from multiprocessing.pool import Pool as PoolCls

# pyelftools
from elftools.dwarf.dwarfinfo import DWARFInfo
from elftools.dwarf.lineprogram import LineState, LineProgram

from capstone import Cs

DEFAULT_BUILD_ID_DIR = os.path.join(os.path.expanduser("~"), ".debug")
"""Default build-id dir"""

NUM_ADDR2LINE_PROCESS = NUM_CORES_PHYSICAL
"""Process number addr2line uses"""

ADDR2LINE_OPT_STRENGTH = 1e9
"""Operation strength to indicate when to parallelize in addr2line"""


def find_addr_by_func_name(symtab, func_name: str) -> Optional[tuple[int, int]]:
    """Find address by function name

    Args:
        symtab : symbol table in elf
        func_name (str): the function name

    Returns:
        Optional[tuple[int, int]]: (start_addr, size)
    """
    symbols = symtab.get_symbol_by_name(func_name)
    if symbols is None:
        return None
    if type(symbols) is list and len(symbols) >= 1:
        sym = symbols[0]
        return (int(sym["st_value"]), sym["st_size"])
    else:
        return None


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
    disa = md.disasm(elfcodes, start_addr)
    func_asm = {}
    for i in disa:
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
    >>> import pipa.service.call_graph as pipa_cfg
    >>> pipa_cfg.NUM_ADDR2LINE_PROCESS = 160
    >>> pipa_cfg.ADDR2LINE_OPT_STRENGTH = 2e8
    >>> dwarfinfo = DWARFInfo(elf)
    >>> addr2lines(dwarfinfo, [0x400000, 0x400001], pool)
    [('main.c', 0x400000, 1, 1), ('main.c', 0x400001, 1, 2)]
    """
    global NUM_ADDR2LINE_PROCESS, ADDR2LINE_OPT_STRENGTH
    parallel = NUM_ADDR2LINE_PROCESS
    operations_strength = ADDR2LINE_OPT_STRENGTH
    if pool._processes < parallel:  # type: ignore
        logger.warning(
            "The pool given to addr2line's processes are small than global setting NUM_ADDR2LINE_PROCESS"
        )
    sourcelines: List[Tuple[str, int, int, int, str]] = []
    state_list: List[Tuple[int, LineState, LineState]] = []
    lineprog_list: List[Tuple[LineProgram, int, str]] = []
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
    address_len = len(addresses)
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
