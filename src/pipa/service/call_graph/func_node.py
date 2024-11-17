from typing import Dict, List, Optional, Tuple
import json
import pandas as pd
import os
import time
from pipa.common.logger import logger
from collections import defaultdict

# multi processing
from multiprocessing import Pool

# pyelftools
from elftools.elf.elffile import ELFFile

# capstone
from capstone import (
    CS_ARCH_ARM,
    CS_ARCH_ARM64,
    CS_MODE_32,
    CS_MODE_ARM,
    CS_MODE_V8,
    CS_ARCH_X86,
    CS_MODE_64,
)

from .addr import (
    DEFAULT_BUILD_ID_DIR,
    find_addr_by_func_name,
    disassemble_func,
    addr2lines,
)

from .node import Node, NodeEncoder, NodeTable


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
    ):
        """
        Initialize a CallGraph object.

        Args:
            func_name (str): The name of the function.
            module_name (str): The name of the module.
            nodes (list[Node] | None): A list of Node objects representing the nodes in the call graph.
                If None, the call graph is empty.
        """
        self.func_name = func_name
        self.module_name = module_name
        self.nodes = nodes
        self.node_infos = node_infos
        self._cycles = sum([node.cycles for node in nodes]) if nodes else 0
        self._instructions = sum([node.instructions for node in nodes]) if nodes else 0

    def __str__(self):
        return f"{self.func_name} {self.module_name}"

    def __hash__(self) -> int:
        return hash(str(self))

    def set_node_infos(self, node_infos: List[Tuple]):
        self.node_infos = node_infos

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
    ):
        """
        Create a CallGraph object from a NodeTable.

        Args:
            node_table (NodeTable): The NodeTable object containing the nodes.
            gen_epm (bool, optional): If True, generate EPM for each function node. Defaults to False.
            buildid_list (Dict[str, str], optional): A dictionary containing build IDs. Not provided as default.
            source_file_prefix (Optional[str], optional): The prefix of all source files. Useful when analysis machine is different from the collected machine. Defaults to None.

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
        RawESL: Dict[str, Dict[str, List[Tuple[int, str, int]]]] = defaultdict(
            lambda: defaultdict(lambda: [])
        )
        for func_node in res.values():
            module_name = func_node.module_name
            func_name = func_node.func_name
            for n in func_node.nodes:  # type: ignore
                if n.function_offset is None:
                    continue
                RawESL[module_name][func_name].append(
                    (n.function_offset, n.addr, n.cycles)
                )
        # Extended Performance Metrics
        EPM: Dict[Tuple[str, str], Dict[str, List[Tuple]]] = defaultdict(
            lambda: defaultdict(lambda: [])
        )
        global NUM_ADDR2LINE_PROCESS
        pool = Pool(NUM_ADDR2LINE_PROCESS)
        for module, funcs in RawESL.items():
            buildid = buildid_list.get(module)
            debug_module = None
            if buildid:
                debug_module = os.path.join(
                    DEFAULT_BUILD_ID_DIR, module.strip("/"), buildid, "elf"
                )
            if debug_module is not None and os.path.exists(debug_module):
                logger.debug(
                    f"Found module {module}'s elf debuginfo file: {debug_module}"
                )
                module = debug_module
            elif not os.path.exists(module):
                logger.warning(f"Not found ELF File {module}")
                continue
            logger.debug(f"Found ELF File {module}")
            logger.debug(f"Start analyze ELF File {module}")
            f = open(module, "rb")
            # open elf file
            elffile = ELFFile(f)
            if not elffile.has_dwarf_info():
                logger.warning(f"{module} has no dwarf info, please provide debuginfo")
                f.close()
                continue
            elf_header = elffile["e_ident"]
            # judge arch and mod
            if elffile["e_machine"] == "EM_386":
                arch = CS_ARCH_X86
                mode = CS_MODE_32
            elif elffile["e_machine"] == "EM_X86_64":
                arch = CS_ARCH_X86
                mode = CS_MODE_64
            elif elffile["e_machine"] == "EM_ARM":
                arch = CS_ARCH_ARM
                if elf_header["EI_CLASS"] == "ELFCLASS32":
                    mode = CS_MODE_ARM
                else:
                    mode = CS_MODE_ARM | CS_MODE_V8
            elif elffile["e_machine"] == "EM_AARCH64":
                arch = CS_ARCH_ARM64
                mode = CS_MODE_ARM
            else:
                logger.warning(f"Unsupported architecture: {elffile['e_machine']}")
                f.close()
                continue
            # get dwarf info
            dwarfinfo = elffile.get_dwarf_info()
            # get symbol table info
            symtable = elffile.get_section_by_name(".symtab")
            if symtable is None:
                logger.warning(
                    f"Not found symtable in elf file {module}, please provide debuginfo."
                )
                f.close()
                continue
            f.seek(0)
            # get elfcodes
            elfcodes = f.read()
            # get module/function info (start addr, func size in bytes)
            # ip_perfs: list of (address, ip, cycles) (detected performance metrics)
            # func_asm: key: address, dict list of (mnemonic, op_str)
            # func_sourcelines: list of (source file, address, line, column)
            # combine info to FunctionNode
            for func_n, ip_perfs in funcs.items():
                # start finnd addr by function name
                logger.debug(f"Start parse {func_n} info in {module}")
                stime = time.perf_counter()
                func_info = find_addr_by_func_name(symtable, func_n)
                etime = time.perf_counter()
                logger.debug(
                    f"End find {func_n} in {module} within {etime - stime} seconds"
                )

                if func_info is None:
                    continue
                func_addr = func_info[0]
                func_size = func_info[1]

                # start disassemble function
                stime = time.perf_counter()
                func_asm = disassemble_func(
                    elfcodes[func_addr : func_addr + func_size],
                    func_addr,
                    arch,
                    mode,
                )
                etime = time.perf_counter()
                logger.debug(
                    f"End disassemble func {func_n} in {module} within {etime - stime} seconds"
                )

                func_addrs = [k for k in func_asm.keys()]

                # start addr2lines
                stime = time.perf_counter()
                func_sourcelines = addr2lines(dwarfinfo, func_addrs, pool=pool)
                etime = time.perf_counter()
                logger.debug(
                    f"End symbolize {func_n} in {module} within {etime - stime} seconds"
                )

                func_node_k = f"{func_n} {module}"
                for addr, asm in func_asm.items():
                    addr_ips = []
                    addr_cycles = 0
                    addr_sourcef = ""
                    addr_relative_dir = ""
                    addr_line = -1
                    addr_column = -1
                    addr_mnemonic = asm[0]
                    addr_op_str = asm[1]
                    for (
                        sourcef,
                        lsaddr,
                        lsline,
                        lscolumn,
                        lsrelative_dir,
                    ) in func_sourcelines:
                        if lsaddr == addr:
                            addr_sourcef = sourcef
                            addr_relative_dir = lsrelative_dir
                            addr_line = lsline
                            addr_column = lscolumn
                            break
                    for iperf in ip_perfs:
                        ioffset, ip, ic = iperf
                        if ioffset + func_addr == addr:
                            addr_ips.append(ip)
                            addr_cycles += ic
                    EPM[(addr_sourcef, addr_relative_dir)][func_node_k].append(
                        (
                            addr,
                            addr_ips,
                            addr_cycles,
                            addr_line,
                            addr_column,
                            addr_mnemonic,
                            addr_op_str,
                        )
                    )
            # at last close module file
            f.close()
        pool.close()
        pool.join()
        for (sourcef, relative_dir), func_nodes in EPM.items():
            sourcefp = (
                os.path.join(source_file_prefix, sourcef)
                if source_file_prefix
                else sourcef
            )
            source_file = sourcefp
            if not os.path.exists(sourcefp):
                d = os.path.join(relative_dir, sourcef)
                if source_file_prefix:
                    d = os.path.join(source_file_prefix, d)
                if not os.path.exists(d):
                    logger.warning(f"source file {d} couldn't found, please check")
                    continue
                else:
                    source_file = d
            stime = time.perf_counter()
            with open(source_file, "r") as f:
                source_conts = f.readlines()
            etime = time.perf_counter()
            logger.debug(
                f"End read source codes in file {source_file} within {etime - stime} seconds"
            )
            for func_node_k, addr_infos in func_nodes.items():
                func_node_infos = []
                for addr_info in addr_infos:
                    addr_line, addr_column = addr_info[3], addr_info[4]
                    if addr_line > 0 and addr_column > 0:
                        addr_conts = source_conts[addr_line - 1]
                    else:
                        continue
                    node_info = (*addr_info, addr_conts, source_file)
                    func_node_infos.append(node_info)
                res[func_node_k].set_node_infos(func_node_infos)
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
