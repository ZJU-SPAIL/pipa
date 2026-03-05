from typing import Dict, List, Optional, Tuple
import json
import pandas as pd
import os
import time
from pipa.common.logger import logger
from pipa.common.utils import process_compression, FileFormat, check_file_format
from pipa.common.hardware.cpu import NUM_CORES_PHYSICAL
from collections import defaultdict
from tempfile import mkdtemp

# multi processing
from multiprocessing import Pool

# pyelftools
from elftools.elf.elffile import ELFFile

from pipa.service.call_graph.addr import (
    DEFAULT_BUILD_ID_DIR,
    disassemble_func,
    addr2lines,
    get_arch_mode,
    get_symbol_addresses,
    get_text_section,
)

from pipa.service.call_graph.node import Node, NodeEncoder, NodeTable


class FunctionNode:
    """
    Represents a function node in the call graph.

    Attributes:
        func_name (str): The name of the function.
        module_name (str): The name of the module containing the function.
        nodes (list[Node] | None): A list of child nodes, if any.
    """

    def __init__(
        self,
        func_name: str,
        module_name: str,
        nodes: list[Node] | None,
        node_infos: Optional[List[Tuple]] = None,
        source_codes: Optional[List[str]] = None,
    ):
        """
        Initialize a CallGraph object.

        Args:
            func_name (str): The name of the function.
            module_name (str): The name of the module.
            nodes (list[Node] | None): A list of Node objects representing the nodes in the call graph.
                If None, the call graph is empty.
            node_infos (list[Tuple], optional): A list of tuples containing information about the instructions / events and source codes.
            source_codes (list[str], optional): Full source codes corresponding to the function node.
        """
        self.func_name = func_name
        self.module_name = module_name
        self.nodes = nodes
        self.node_infos = node_infos
        self.source_codes = source_codes
        self._cycles = sum([node.cycles for node in nodes]) if nodes else 0
        self._instructions = sum([node.instructions for node in nodes]) if nodes else 0

    def __str__(self):
        return f"{self.func_name} {self.module_name}"

    def __hash__(self) -> int:
        return hash(str(self))

    def set_node_infos(self, node_infos: List[Tuple]):
        self.node_infos = node_infos

    def set_source_codes(self, source_codes: List[str]):
        self.source_codes = source_codes

    def extend_node_infos(self, node_infos: List[Tuple]):
        if not self.node_infos:
            self.node_infos = node_infos
        else:
            self.node_infos.extend(node_infos)

    def extend_source_codes(self, source_codes: List[str]):
        if not self.source_codes:
            self.source_codes = source_codes
        else:
            self.source_codes.extend(source_codes)

    def get_cycles(self):
        cycles_cur = sum([node.cycles for node in self.nodes]) if self.nodes else 0
        self._cycles = cycles_cur
        return cycles_cur

    def get_instructions(self):
        instructions_cur = (
            sum([node.instructions for node in self.nodes]) if self.nodes else 0
        )
        self._instructions = instructions_cur
        return instructions_cur

    def get_events_values(self):
        ev: Dict[str, int] = defaultdict(lambda: 0)
        for n in self.nodes:
            for e, v in n.events.items():
                ev[e] += v
        return ev


class FunctionNodeTable:
    """
    A class representing a table of function nodes.

    This class provides a dictionary-like interface to store and manipulate function nodes.

    Attributes:
        function_nodes (dict[str, FunctionNode]): A dictionary that stores function nodes.

    Methods:
        __getitem__(self, key: str) -> FunctionNode: Returns the function node associated with the given key.
        __setitem__(self, key: str, value: FunctionNode): Sets the function node associated with the given key.
        __iter__(self): Returns an iterator over the function nodes.
        __len__(self): Returns the number of function nodes in the table.
        __str__(self): Returns a string representation of the function node table.
        __repr__(self): Returns a string representation of the function node table.
        __contains__(self, key): Checks if the table contains a function node with the given key.
        __delitem__(self, key): Deletes the function node associated with the given key.
        __add__(self, other): Returns a new function node table that is the union of this table and another table.
        __sub__(self, other): Returns a new function node table that contains the function nodes in this table but not in another table.
        __and__(self, other): Returns a new function node table that contains the function nodes that are common to both this table and another table.
        __or__(self, other): Returns a new function node table that is the union of this table and another table.
        __xor__(self, other): Returns a new function node table that contains the function nodes that are in either this table or another table, but not in both.
        __eq__(self, other): Checks if this function node table is equal to another function node table.
        __ne__(self, other): Checks if this function node table is not equal to another function node table.
        __lt__(self, other): Checks if this function node table is less than another function node table.
        __le__(self, other): Checks if this function node table is less than or equal to another function node table.
        __gt__(self, other): Checks if this function node table is greater than another function node table.
        __ge__(self, other): Checks if this function node table is greater than or equal to another function node table.
        from_node_table(cls, node_table: NodeTable): Creates a new function node table from a node table.

    """

    def __init__(self, function_nodes: dict[str, FunctionNode] | None = None):
        self.function_nodes = function_nodes if function_nodes else {}

    def __getitem__(self, key: str) -> FunctionNode:
        return self.function_nodes[key]

    def __setitem__(self, key: str, value: FunctionNode):
        self.function_nodes[key] = value

    def __iter__(self):
        return iter(self.function_nodes)

    def __len__(self):
        return len(self.function_nodes)

    def __str__(self):
        return str(self.function_nodes)

    def __repr__(self):
        return repr(self.function_nodes)

    def __contains__(self, key):
        return key in self.function_nodes

    def __delitem__(self, key):
        del self.function_nodes[key]

    def __add__(self, other):
        return FunctionNodeTable({**self.function_nodes, **other.function_nodes})

    def __sub__(self, other):
        return FunctionNodeTable(
            {
                k: v
                for k, v in self.function_nodes.items()
                if k not in other.function_nodes
            }
        )

    def __and__(self, other):
        return FunctionNodeTable(
            {k: v for k, v in self.function_nodes.items() if k in other.function_nodes}
        )

    def __or__(self, other):
        return FunctionNodeTable({**self.function_nodes, **other.function_nodes})

    def __xor__(self, other):
        return FunctionNodeTable(
            {
                k: v
                for k, v in self.function_nodes.items()
                if k not in other.function_nodes
            }
            | {
                k: v
                for k, v in other.function_nodes.items()
                if k not in self.function_nodes
            }
        )

    def __eq__(self, other):
        return self.function_nodes == other.function_nodes

    def __ne__(self, other):
        return self.function_nodes != other.function_nodes

    def __lt__(self, other):
        return self.function_nodes < other.function_nodes

    def __le__(self, other):
        return self.function_nodes <= other.function_nodes

    def __gt__(self, other):
        return self.function_nodes > other.function_nodes

    def __ge__(self, other):
        return self.function_nodes >= other.function_nodes

    @classmethod
    def from_node_table(
        cls,
        node_table: NodeTable,
        gen_epm: bool = False,
        buildid_list: Dict[str, str] = {},
        source_file_prefix: Optional[str] = None,
        addr2lines_processes: int = NUM_CORES_PHYSICAL,
    ):
        """
        Create a CallGraph object from a NodeTable.

        Args:
            node_table (NodeTable): The NodeTable object containing the nodes.
            gen_epm (bool, optional): If True, generate EPM for each function node. Defaults to False.
            buildid_list (Dict[str, str], optional): A dictionary containing build IDs. Not provided as default.
            source_file_prefix (Optional[str], optional): The prefix of all source files. Useful when analysis machine is different from the collected machine. Defaults to None.
            addr2lines_processes (int, optional): The number of processes used for addr2lines. Defaults to NUM_CORES_PHYSICAL.

        Returns:
            CallGraph: The CallGraph object created from the NodeTable.
        """
        res: Dict[str, FunctionNode] = {}
        for node in node_table._nodes.values():
            method_name = node.get_function_name()
            module_name = node.caller
            k = f"{method_name} {module_name}"
            if k not in res:
                res[k] = FunctionNode(
                    func_name=method_name, module_name=module_name, nodes=[node]
                )
            else:
                res[k].nodes.append(node)  # type: ignore
        if not gen_epm:
            return cls(function_nodes=res)
        # generate EPM
        logger.debug("Start generate Extended Performance Metrics")
        # RalESL: module -> function -> (offset, addr, cycles, more events metrics)
        RawESL: Dict[str, Dict[str, List[Tuple[int, str, int, Dict[str, int]]]]] = (
            defaultdict(lambda: defaultdict(lambda: []))
        )
        for func_node in res.values():
            for n in func_node.nodes:  # type: ignore
                if n.function_offset is None:
                    continue
                RawESL[func_node.module_name][func_node.func_name].append(
                    (n.function_offset, n.addr, n.cycles, n.events.copy())
                )
        # Extended Performance Metrics
        EPM: Dict[Tuple[str, str], Dict[str, List[Tuple]]] = defaultdict(
            lambda: defaultdict(lambda: [])
        )
        pool = Pool(addr2lines_processes)
        for module, funcs in RawESL.items():
            # determine the module for analysis
            esl_module = module
            buildid = buildid_list.get(module)
            debug_module = None
            if buildid:
                debug_module = os.path.join(
                    DEFAULT_BUILD_ID_DIR, module.strip("/"), buildid, "elf"
                )
            if debug_module is not None and os.path.exists(debug_module):
                logger.debug(
                    f"Found module {module}'s seperated debuginfo file: {debug_module}"
                )
                module = debug_module
            elif not os.path.exists(module):
                logger.warning(f"Not found ELF File {module}")
                continue
            logger.debug(f"Start analyze ELF File {module}")
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
                        f"Extract {module} to {tmpd}. But expected {extracted} not found"
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
            # judge arch and mod
            try:
                arch, mode = get_arch_mode(elffile)
            except NotImplementedError as e:
                logger.warning(f"{module} has unsupported arch or mode: {e}")
                f.close()
                continue
            # get dwarf info
            dwarfinfo = elffile.get_dwarf_info()
            # check dwarf info has debug info
            if not dwarfinfo.has_debug_info:
                logger.warning(
                    f"{module}'s dwarf lost debuginfo, source codes may not be found. Please check your compile methods"
                )
            # get symbol table info
            symtable = elffile.get_section_by_name(".symtab")
            if symtable is None:
                logger.warning(
                    f"Not found symtable in {module}, please provide debuginfo."
                )
                f.close()
                continue
            # get all functions' start address / name / size in the elffile
            function_address_size_info = get_symbol_addresses(
                elffile=elffile, func_name=None
            )
            # get text section's info to calculate the offset of each function
            try:
                text_data, text_addr = get_text_section(elffile=elffile)
                text_data_len = len(text_data)
            except ValueError as e:
                logger.warning(f"{module} has no text section: {e}")
                f.close()
                continue
            # get module/function info (start addr, func size in bytes)
            # ip_perfs: list of (address, ip, cycles, more events metrics) (detected performance metrics)
            # func_asm: key: address, dict list of (mnemonic, op_str)
            # func_sourcelines: list of (source file, address, line, column)
            # combine info to FunctionNode
            for func_n, ip_perfs in funcs.items():
                # get function info by function name
                func_info = function_address_size_info.get(func_n)
                if func_info is None:
                    continue

                # calculate function offset
                func_addr, func_size = func_info
                func_offset = func_addr - text_addr
                if func_offset < 0 or func_offset + func_size > text_data_len:
                    logger.warning(
                        f"function {func_n}'s offset is out of the .text section's range"
                    )
                    continue

                # start disassemble function
                func_asm = disassemble_func(
                    text_data[func_offset : func_offset + func_size],
                    func_addr,
                    arch,
                    mode,
                )

                # get function's addresses
                func_addrs = [k for k in func_asm.keys()]

                # start addr to source lines
                stime = time.perf_counter()
                func_sourcelines = addr2lines(dwarfinfo, func_addrs, pool=pool)
                etime = time.perf_counter()
                logger.debug(
                    f"End symbolize {func_n} in {module} within {etime - stime} seconds"
                )

                # func_node_k should be equal to what in ESL.
                func_node_k = f"{func_n} {esl_module}"
                for addr, asm in func_asm.items():
                    addr_ips = []
                    addr_cycles = 0
                    addr_source_file = ""
                    addr_relative_dir = ""
                    addr_line = -1
                    addr_column = -1
                    addr_mnemonic = asm[0]
                    addr_op_str = asm[1]
                    addr_other_events: Dict[str, int] = defaultdict(lambda: 0)
                    # TODO seems like we can use addr as func_sourcelines's key, as it may be same as the key in func_asm, each key can store multi data
                    for func_source_mapping_info in func_sourcelines:
                        source_file, lsaddr, lsline, lscolumn, lsrelative_dir = (
                            func_source_mapping_info
                        )
                        if lsaddr == addr:
                            addr_source_file = source_file
                            addr_relative_dir = lsrelative_dir
                            addr_line = lsline
                            addr_column = lscolumn
                            break
                    for iperf in ip_perfs:
                        ioffset, ip, ic, other_events = iperf
                        if ioffset + func_addr == addr:
                            addr_ips.append(ip)
                            addr_cycles += ic
                            for e, v in other_events.items():
                                addr_other_events[e] += v
                    # when source codes (debuginfo) lost, the key will be ("", "")
                    # key is (source_file, relative_dir)
                    # some func / module may share same sourcefiles, use this kind of key to reduce times of reading sourcecodes
                    EPM[(addr_source_file, addr_relative_dir)][func_node_k].append(
                        (
                            addr,
                            addr_ips,
                            addr_cycles,
                            addr_line,
                            addr_column,
                            addr_mnemonic,
                            addr_op_str,
                            addr_other_events,
                        )
                    )
            # at last close module file
            f.close()
        pool.close()
        pool.join()
        # start get source codes
        for (source_file_raw, relative_dir), func_nodes in EPM.items():
            # source_file_prefix ignores /
            # get source file's contents
            source_file_with_prefix = (
                f"{source_file_prefix}/{source_file_raw}"
                if source_file_prefix
                else source_file_raw
            )
            source_file = source_file_with_prefix
            if not os.path.exists(source_file_with_prefix):
                relative_source_file_with_prefix = os.path.join(
                    relative_dir, source_file_raw
                )
                if source_file_prefix:
                    relative_source_file_with_prefix = (
                        f"{source_file_prefix}/{relative_source_file_with_prefix}"
                    )
                source_file = relative_source_file_with_prefix
            if os.path.isdir(source_file):
                logger.warning(f"{source_file} is directory, can't read")
                continue
            if not os.path.exists(source_file):
                logger.warning(
                    f"source file {source_file} couldn't found, please check"
                )
                continue
            with open(source_file, "r") as f:
                source_conts = f.readlines()
            # for each function node, get its info and stored it in its node_info attrs
            for func_node_k, addr_infos in func_nodes.items():
                lines = []
                func_node_infos = []
                for addr_info in addr_infos:
                    addr_line, addr_column = addr_info[3], addr_info[4]
                    if addr_line > 0 and addr_column > 0:
                        lines.append(addr_line - 1)
                        addr_conts = source_conts[addr_line - 1]
                    else:
                        continue
                    node_info = (*addr_info, addr_conts, source_file)
                    func_node_infos.append(node_info)
                lines.sort()
                # a function may has multiple corresponding source files
                # a sourcefile may has multiple corresponding functions
                res[func_node_k].extend_source_codes(
                    source_conts[lines[0] : lines[-1] + 1]
                )
                res[func_node_k].extend_node_infos(func_node_infos)
        return cls(function_nodes=res)

    def to_dataframe(self):
        data = [
            {
                "function_name": v.func_name,
                "module_name": v.module_name,
                "cycles": v.get_cycles(),
                "instructions": v.get_instructions(),
            }
            for v in self.function_nodes.values()
        ]
        return pd.DataFrame(data)

    def copy(self):
        return FunctionNodeTable({k: v for k, v in self.function_nodes.items()})


class ClusterEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Node):
            return NodeEncoder().default(obj)
        return super().default(obj)
