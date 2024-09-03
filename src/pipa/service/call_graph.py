from typing import Dict, List, Literal, Mapping, Optional, Tuple
import networkx as nx
import json
import matplotlib.pyplot as plt
import pandas as pd
import os
import time
from pipa.common.logger import logger
from pipa.common.hardware.cpu import NUM_CORES_PHYSICAL
from pipa.common.utils import find_closet_factor_pair
from pipa.parser.perf_script_call import PerfScriptData
from networkx.drawing.nx_pydot import write_dot
from collections import defaultdict

# multi processing
from multiprocessing import Pool
from multiprocessing.pool import Pool as PoolCls

# pyelftools
from elftools.elf.elffile import ELFFile
from elftools.dwarf.dwarfinfo import DWARFInfo
from elftools.dwarf.lineprogram import LineState, LineProgram

# capstone
from capstone import (
    CS_ARCH_ARM,
    CS_ARCH_ARM64,
    CS_MODE_32,
    CS_MODE_ARM,
    CS_MODE_V8,
    Cs,
    CS_ARCH_X86,
    CS_MODE_64,
)


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
    address_len = len(addresses)
    state_len = len(state_list)
    operations_len = address_len * state_len
    logger.debug(f"\t addresses len: {address_len}")
    logger.debug(f"\t state tuple len: {state_len}")
    if operations_len < operations_strength:
        # sequential addr2line
        for state_tuple in state_list:
            for address in addresses:
                # Found address
                lineprog_index, prevstate, state = state_tuple
                lineprog, delta, relative_dir = lineprog_list[lineprog_index]
                if prevstate.address <= address < state.address:
                    file_entry = lineprog["file_entry"][prevstate.file - delta]
                    file_name = file_entry.name.decode("utf-8")
                    dir_index = file_entry.dir_index
                    dir_name = lineprog["include_directory"][dir_index - delta].decode(
                        "utf-8"
                    )
                    file_name = f"{dir_name}/{file_name}"
                    sourcelines.append(
                        (
                            file_name,
                            address,
                            prevstate.line,
                            prevstate.column,
                            relative_dir,
                        )
                    )
                    address_len -= 1
                if address_len <= 0:
                    return sourcelines
    else:
        logger.debug(
            f"\t {operations_len} >= {operations_strength}, will use parallel {parallel} processes to addr2line"
        )

        # allocate tasks
        stime = time.perf_counter()
        m, n = find_closet_factor_pair(parallel)
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
                dir_name = lineprog["include_directory"][dir_index - delta].decode(
                    "utf-8"
                )
                file_name = f"{dir_name}/{file_name}"
                sourcelines.append(
                    (file_name, addr, pvstate.line, pvstate.column, relative_dir)
                )
                address_len -= 1
                if address_len <= 0:
                    return sourcelines
    logger.warning("\t Not all address found sourcelines mapped")
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
            if prevstate.address <= address < state.address:
                result.append((lineprog_index, address, prevstate))
    return result


class Node:
    """
    Represents a node in the call graph.

    Attributes:
        addr (str): The address of the node.
        symbol (str): The symbol of the node.
        caller (str): The caller of the node.
        command (str | None, optional): The command associated with the node. Defaults to None.
        cycles (int, optional): The number of cycles. Defaults to 0.
        instructions (int, optional): The number of instructions. Defaults to 0.
    """

    def __init__(
        self,
        addr: str,
        symbol: str,
        caller: str,
        command: str | None = None,
        cycles: int = 0,
        instructions: int = 0,
    ):
        """
        Initialize a CallGraph Node object.

        Args:
            addr (str): The address of the call graph node.
            symbol (str): The symbol of the call graph node.
            caller (str): The caller of the call graph node.
            command (str | None, optional): The command associated with the call graph node. Defaults to None.
            cycles (int, optional): The number of cycles in the call graph node. Defaults to 0.
            instructions (int, optional): The number of instructions in the call graph node. Defaults to 0.
        """
        # Instruction Pointer
        self.addr = addr

        # function symbol
        self.symbol = symbol
        _symbol_split = self.symbol.split("+", maxsplit=1)
        self.function_name = _symbol_split[0]
        self.function_offset = (
            int(_symbol_split[1], 16) if len(_symbol_split) == 2 else None
        )

        self.caller = caller
        self.command = command
        self.cycles = cycles
        self.instructions = instructions

    def get_function_name(self):
        return self.function_name

    def get_offset(self) -> Optional[int]:
        return self.function_offset


class NodeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Node):
            return {
                "addr": obj.addr,
                "symbol": obj.symbol,
                "caller": obj.caller,
                "command": obj.command,
                "cycles": obj.cycles,
                "instructions": obj.instructions,
            }
        return super().default(obj)


class NodeTable:
    """
    A class representing a table of nodes.

    This class provides a dictionary-like interface for managing nodes.

    Attributes:
        _nodes (dict): The dictionary containing the nodes.

    Methods:
        __init__(self, nodes: dict | None = None): Initializes the NodeTable.
        __getitem__(self, key): Retrieves a node from the NodeTable.
        __setitem__(self, key, value): Sets a node in the NodeTable.
        __iter__(self): Returns an iterator for the NodeTable.
        __len__(self): Returns the number of nodes in the NodeTable.
        __str__(self): Returns a string representation of the NodeTable.
        __repr__(self): Returns a string representation of the NodeTable.
        __contains__(self, key): Checks if a node exists in the NodeTable.
        __delitem__(self, key): Deletes a node from the NodeTable.
        __add__(self, other): Returns a new NodeTable with nodes from both tables.
        __sub__(self, other): Returns a new NodeTable with nodes not present in the other table.
        __and__(self, other): Returns a new NodeTable with nodes present in both tables.
        __or__(self, other): Returns a new NodeTable with nodes from either table.
        __xor__(self, other): Returns a new NodeTable with nodes present in only one of the tables.
        __eq__(self, other): Checks if two NodeTables are equal.
        __ne__(self, other): Checks if two NodeTables are not equal.
        __lt__(self, other): Checks if one NodeTable is less than the other.
        __le__(self, other): Checks if one NodeTable is less than or equal to the other.
        __gt__(self, other): Checks if one NodeTable is greater than the other.
        __ge__(self, other): Checks if one NodeTable is greater than or equal to the other.
        from_perf_script_data(cls, perf_script: PerfScriptData, pids: list | None = None, cpus: list | None = None): Creates a NodeTable from a PerfScriptData object.
        from_perf_script_file(cls, perf_script_file: str, pids: list | None = None, cpus: list | None = None): Creates a NodeTable from a perf script file.
    """

    def __init__(self, nodes: dict | None = None):
        """
        Initializes a node table object.

        Args:
            nodes (dict | None): A dictionary representing the nodes of the call graph.
                Defaults to None if not provided.

        Returns:
            None
        """
        self._nodes = nodes if nodes else {}

    def __getitem__(self, key):
        return self._nodes[key]

    def __setitem__(self, key, value):
        self._nodes[key] = value

    def __iter__(self):
        return iter(self._nodes)

    def __len__(self):
        return len(self._nodes)

    def __str__(self):
        return str(self._nodes)

    def __repr__(self):
        return repr(self._nodes)

    def __contains__(self, key):
        return key in self._nodes

    def __delitem__(self, key):
        del self._nodes[key]

    def __add__(self, other):
        return NodeTable({**self._nodes, **other._nodes})

    def __sub__(self, other):
        return NodeTable(
            {k: v for k, v in self._nodes.items() if k not in other._nodes}
        )

    def __and__(self, other):
        return NodeTable({k: v for k, v in self._nodes.items() if k in other._nodes})

    def __or__(self, other):
        return NodeTable({**self._nodes, **other._nodes})

    def __xor__(self, other):
        return NodeTable(
            {k: v for k, v in self._nodes.items() if k not in other._nodes}
            | {k: v for k, v in other._nodes.items() if k not in self._nodes}
        )

    def __eq__(self, other):
        return self._nodes == other._nodes

    def __ne__(self, other):
        return self._nodes != other._nodes

    def __lt__(self, other):
        return self._nodes < other._nodes

    def __le__(self, other):
        return self._nodes <= other._nodes

    def __gt__(self, other):
        return self._nodes > other._nodes

    def __ge__(self, other):
        return self._nodes >= other._nodes

    @classmethod
    def from_perf_script_data(
        cls,
        perf_script: PerfScriptData,
        pids: list | None = None,
        cpus: list | None = None,
    ):
        """
        Create a node table from PerfScriptData.

        Args:
            perf_script (PerfScriptData): The PerfScriptData object containing the performance script data.
            pids (list | None, optional): The PIDs to filter the data by. Defaults to None.
            cpus (list | None, optional): The CPUs to filter the data by. Defaults to None.

        Returns:
            cls: An instance of the class with the call graph created from the PerfScriptData.

        """
        if pids is not None:
            perf_script = perf_script.filter_by_pids(pids=pids)
        if cpus is not None:
            perf_script = perf_script.filter_by_cpus(cpus=cpus)

        res = {}
        for block in perf_script.blocks:
            header = block.header
            calls = block.calls

            if not calls:
                continue

            addr = calls[0].addr
            if addr in res:
                if header.event == "cycles":
                    res[addr].cycles += header.value
                elif header.event == "instructions":
                    res[addr].instructions += header.value
            else:
                res[addr] = Node(
                    addr=calls[0].addr,
                    symbol=calls[0].symbol,
                    caller=calls[0].caller,
                    command=header.command,
                    cycles=header.value if header.event == "cycles" else 0,
                    instructions=header.value if header.event == "instructions" else 0,
                )
            for i in range(1, len(calls)):
                if calls[i].addr not in res:
                    res[calls[i].addr] = Node(
                        addr=calls[i].addr,
                        symbol=calls[i].symbol,
                        caller=calls[i].caller,
                    )

        return cls(nodes=res)

    def copy(self):
        return NodeTable({k: v for k, v in self._nodes.items()})

    @classmethod
    def from_perf_script_file(
        cls, perf_script_file: str, pids: list | None = None, cpus: list | None = None
    ):
        """
        Create a CallGraph instance from a perf script file.

        Args:
            perf_script_file (str): The path to the perf script file.

        Returns:
            CallGraph: The CallGraph instance created from the perf script file.
        """
        return cls.from_perf_script_data(
            PerfScriptData.from_file(perf_script_file), pids=pids, cpus=cpus
        )

    def to_dataframe(self):
        data = [
            {
                "addr": v.addr,
                "symbol": v.symbol,
                "caller": v.caller,
                "command": v.command,
                "cycles": v.cycles,
                "instructions": v.instructions,
            }
            for v in self._nodes.values()
        ]
        return pd.DataFrame(data)


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
    def from_node_table(cls, node_table: NodeTable):
        """
        Create a CallGraph object from a NodeTable.

        Args:
            node_table (NodeTable): The NodeTable object containing the nodes.

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
            if not os.path.exists(module):
                continue
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
                    elfcodes[func_addr : func_addr + func_size], func_addr, arch, mode
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
            source_file = sourcef
            if not os.path.exists(sourcef):
                d = os.path.join(relative_dir, sourcef)
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


class CallGraph:
    """
    Represents a call graph.

    Attributes:
        block_graph (nx.DiGraph): The directed graph representing the call relationships at the block level.
        node_table (NodeTable): The table mapping node addresses to node objects.
        func_graph (nx.DiGraph): The directed graph representing the call relationships at the function level.
        function_node_table (FunctionNodeTable): The table mapping function names to function nodes.
    """

    def __init__(
        self,
        block_graph: nx.DiGraph | None = None,
        node_table: NodeTable | None = None,
        func_graph: nx.DiGraph | None = None,
        function_node_table: FunctionNodeTable | None = None,
    ):
        """
        Initializes a CallGraph object.

        Args:
            block_graph (nx.DiGraph, optional): The directed graph representing the call relationships at blocks level.
                Defaults to None.
            node_table (NodeTable, optional): The table mapping node addresses to node objects.
                Defaults to None.
            func_graph (nx.DiGraph, optional): The directed graph representing the call relationships at function level.
                Defaults to None.
            function_node_table (FunctionNodeTable, optional): The table mapping function names to function nodes.
                Defaults to None.
        """
        self.block_graph = nx.DiGraph() if block_graph is None else block_graph
        self.node_table = NodeTable() if node_table is None else node_table
        self.func_graph = nx.DiGraph() if func_graph is None else func_graph
        self.function_node_table = (
            FunctionNodeTable.from_node_table(self.node_table)
            if function_node_table is None
            else function_node_table
        )

    @classmethod
    def from_perf_script_data(
        cls,
        perf_script: PerfScriptData,
        pids: list | None = None,
        cpus: list | None = None,
    ):
        """
        Creates a CallGraph object from performance script data.

        Args:
            perf_script (PerfScriptData): The performance script data.
            pid (int, optional): The process ID. Defaults to None.
            cpu (int, optional): The CPU ID. Defaults to None.

        Returns:
            CallGraph: The CallGraph object created from the performance script data.
        """
        if pids is not None:
            perf_script = perf_script.filter_by_pids(pids=pids)
        if cpus is not None:
            perf_script = perf_script.filter_by_cpus(cpus=cpus)

        node_table = NodeTable.from_perf_script_data(perf_script)
        block_graph = nx.DiGraph()

        func_table = FunctionNodeTable.from_node_table(node_table)
        func_graph = nx.DiGraph()

        for block in perf_script.blocks:
            calls = block.calls
            for i in range(1, len(calls)):
                caller = calls[i - 1].addr
                callee = calls[i].addr
                block_graph.add_edge(node_table[callee], node_table[caller], weight=1)
                k_caller = f"{node_table[caller].get_function_name()} {node_table[caller].caller}"
                k_callee = f"{node_table[callee].get_function_name()} {node_table[callee].caller}"
                func_caller = func_table[k_caller]
                func_callee = func_table[k_callee]
                if func_graph.has_edge(func_callee, func_caller):
                    func_graph[func_callee][func_caller]["weight"] += 1
                else:
                    func_graph.add_edge(
                        func_callee,
                        func_caller,
                        weight=1,
                    )

        return cls(
            block_graph=block_graph,
            node_table=node_table,
            func_graph=func_graph,
            function_node_table=func_table,
        )

    def simple_groups(
        self,
        fig_path: str = "simple_groups.png",
        cluster_info_path: str = "simple_groups_cluster.txt",
        supergraph_layout_scale: int = 50,
        supergraph_layout_seed: int = 429,
        supergraph_layout_k: Optional[float] = None,
        supergraph_layout_iters: int = 50,
        nodegroup_layout_scale: int = 1,
        nodegroup_layout_seed: int = 1430,
        nodegroup_layout_k: Optional[float] = None,
        nodegroup_layout_iters: int = 50,
    ):
        """
        Simply group graph with its module name

        Args:
            fig_path (str, optional): Save figure to file. Defaults to "simple_groups.png".
            cluster_info_path (str, optional): Save raw cluster data to file. Defaults to "simple_groups_cluster.txt".
            supergraph_layout_scale (int, optional): The whole graph's layout scale param. Defaults to 50.
            supergraph_layout_seed (int, optional): The whole graph's layout seed param. Defaults to 429.
            supergraph_layout_k (Optional[float], optional): The whole graph's layout k param. Defaults to None.
            supergraph_layout_iters (int, optional): The whole graph's layout iters param. Defaults to 100.
            nodegroup_layout_scale (int, optional): Each node group graph's layout scale param. Defaults to 20.
            nodegroup_layout_seed (int, optional): The node group graph's layout seed param. Defaults to 1430.
            nodegroup_layout_k (Optional[float], optional): The node group graph's layout k param. Defaults to None.
            nodegroup_layout_iters (int, optional): The node group graph's layout iters param. Defaults to 100.

        Examples:
        >>> from pipa.service.call_graph import CallGraph
        >>> from pipa.parser.perf_script_call import PerfScriptData
        >>> data = PerfScriptData.from_file("perf.script")
        >>> cfg = CallGraph.from_perf_script_data(data)
        >>> cfg.simple_groups()
        """
        G = self.func_graph
        nodes = G.nodes

        # create groups
        attrs_groups = defaultdict(lambda: [])
        for node in nodes:
            attr = f"{node.module_name}"
            attrs_groups[attr].append(node)
        attrs_to_cluster = {attr: idx for idx, attr in enumerate(attrs_groups.keys())}

        # assign cluster & Combine Data
        _clusters = defaultdict(lambda: {"cycles": 0, "insts": 0, "funcs": []})
        for node, node_v in nodes.items():
            attr = f"{node.module_name}"
            _cluster = attrs_to_cluster[attr]
            node_v["cluster"] = _cluster
            _clusters[_cluster]["cycles"] += node.get_cycles()
            _clusters[_cluster]["insts"] += node.get_instructions()
            _clusters[_cluster]["funcs"].extend(node.nodes)  # type: ignore
            # for sub_node in node.nodes:
        with open(cluster_info_path, "w") as file:
            json.dump(_clusters, file, cls=ClusterEncoder, indent=4)

        # use viridis colors for mapping
        color_map = plt.get_cmap("viridis", len(attrs_groups))

        # set color for the group results
        node_colors = [color_map(node_v["cluster"]) for node_v in nodes.values()]
        for i, node_v in enumerate(nodes.values()):
            node_v["color"] = node_colors[i]

        # fetch each node's position
        # group nodes
        pos = {}
        node_groups = [frozenset(nodes) for nodes in attrs_groups.values()]
        superpos = nx.spring_layout(
            G,
            scale=supergraph_layout_scale,
            seed=supergraph_layout_seed,
            k=supergraph_layout_k,
            iterations=supergraph_layout_iters,
        )
        centers = list(superpos.values())
        for center, comm in zip(centers, node_groups):
            pos.update(
                nx.spring_layout(
                    nx.subgraph(G, comm),
                    center=center,
                    scale=nodegroup_layout_scale,
                    seed=nodegroup_layout_seed,
                    k=nodegroup_layout_k,
                    iterations=nodegroup_layout_iters,
                )
            )

        # specify node's name
        node_names = {}
        for node in nodes:
            node_names[node] = (
                f"{node}\ncycles: {node.get_cycles()}\ninsts: {node.get_instructions()}"
            )

        # print fig
        self.show(
            graph="func_graph",
            node_names=node_names,
            pos=pos,
            fig_path=fig_path,
            node_color=node_colors,
            node_groups=node_groups,
        )

    def show(
        self,
        pos: Optional[Mapping] = None,
        node_names: Optional[Mapping] = None,
        graph: Literal["block_graph", "func_graph"] = "func_graph",
        layout_scale: int = 3,
        fig_path: Optional[str] = None,
        node_color: str | list = "skyblue",
        fig_size: tuple[int, int] = (100, 100),
        node_size: int = 700,
        font_size: int = 12,
        font_weight: Literal["normal", "bold"] = "normal",
        node_groups: Optional[list] = None,
    ):
        """
        Displays the call graph.

        Args:
            pos (Optional[Mapping], optional): The graph nodes' position data, if None is passed will calculated using default spring_layout. Defaults to None.
            node_names (Optional[Mapping], optional): The graph nodes' name. Defaults to None.
            graph (Literal[&quot;block_graph&quot;, &quot;func_graph&quot;], optional): Which type of graph to show. Defaults to "func_graph".
            layout_scale (int, optional): default spring_layout's scale param. Defaults to 3.
            fig_path (Optional[str], optional): The path to save the call graph figure. Defaults to None.
            node_color (str | list, optional): The graph nodes' color. Defaults to "skyblue". Can be a list
            fig_size (tuple[int, int], optional): The figure size. Defaults to (100, 100).
            node_size (int, optional): The graph nodes' size. Defaults to 700.
            font_size (int, optional): The font size in figure. Defaults to 12.
            font_weight (Literal[&quot;normal&quot;, &quot;bold&quot;], optional): The font weight in figure. Defaults to "normal".
            node_groups (Optional[list], optional): Use node groups to draw nodes separately. Defaults to None.
        """
        G = self.__getattribute__(graph)
        plt.figure(figsize=fig_size)

        # require node positions
        if not pos:
            pos = nx.spring_layout(G, scale=layout_scale)

        # draw edges' label
        edge_labels = nx.get_edge_attributes(G, "weight")
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)

        # draw nodes
        if node_groups:
            for nodes in node_groups:
                nx.draw_networkx_nodes(G, pos=pos, nodelist=nodes)

        # draw graph with additional information
        nx.draw(
            G,
            pos,
            labels=node_names,
            with_labels=True,
            node_size=node_size,
            node_color=node_color,
            font_size=font_size,
            font_weight=font_weight,
        )

        # print figure
        plt.tight_layout()
        if fig_path:
            plt.savefig(fig_path)
        plt.show()

    def save_dot(self, dot_path: str):
        """
        Saves the call graph dot file.

        Args:
            dot_path (str): The path to save the call graph.

        Returns:
            None
        """
        write_dot(self.block_graph, dot_path)
