import networkx as nx
import matplotlib.pyplot as plt
from pipa.parser.perf_script_call import PerfScriptData


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
        self.addr = addr
        self.symbol = symbol
        self.caller = caller
        self.command = command
        self.cycles = cycles
        self.instructions = instructions


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
        from_perf_script_data(cls, perf_script: PerfScriptData, pid: int | None = None, cpu: int | None = None): Creates a NodeTable from PerfScriptData.
        from_perf_script_file(cls, perf_script_file: str, pid: int | None = None, cpu: int | None = None): Creates a NodeTable from a perf script file.
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
        cls, perf_script: PerfScriptData, pid: int | None = None, cpu: int | None = None
    ):
        """
        Create a node table from PerfScriptData.

        Args:
            perf_script (PerfScriptData): The PerfScriptData object containing the performance script data.
            pid (int | None, optional): The process ID to filter the data by. Defaults to None.
            cpu (int | None, optional): The CPU ID to filter the data by. Defaults to None.

        Returns:
            cls: An instance of the class with the call graph created from the PerfScriptData.

        """
        if pid is not None:
            perf_script = perf_script.filter_by_pid(pid=pid)
        if cpu is not None:
            perf_script = perf_script.filter_by_cpu(cpu=cpu)

        res = {}
        for block in perf_script.blocks:
            header = block.header
            calls = block.calls
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

    @classmethod
    def from_perf_script_file(
        cls, perf_script_file: str, pid: int | None = None, cpu: int | None = None
    ):
        """
        Create a CallGraph instance from a perf script file.

        Args:
            perf_script_file (str): The path to the perf script file.
            pid (int | None, optional): The process ID to filter the call graph for. Defaults to None.
            cpu (int | None, optional): The CPU to filter the call graph for. Defaults to None.

        Returns:
            CallGraph: The CallGraph instance created from the perf script file.
        """
        return cls.from_perf_script_data(
            PerfScriptData.from_file(perf_script_file), pid=pid, cpu=cpu
        )


class CallGraph:
    """
    Represents a call graph.

    Attributes:
        directed_graph (nx.DiGraph): The directed graph representing the call relationships.
        node_table (NodeTable): The table mapping node addresses to node objects.
    """

    def __init__(
        self,
        directed_graph: nx.DiGraph | None = None,
        node_table: NodeTable | None = None,
    ):
        """
        Initializes a CallGraph object.

        Args:
            directed_graph (nx.DiGraph, optional): The directed graph representing the call relationships.
                Defaults to None.
            node_table (NodeTable, optional): The table mapping node addresses to node objects.
                Defaults to None.
        """
        self.directed_graph = nx.DiGraph() if directed_graph is None else directed_graph
        self.node_table = NodeTable() if node_table is None else node_table

    def __str__(self):
        """
        Returns a string representation of the call graph.

        Returns:
            str: The string representation of the call graph.
        """
        return str(self.directed_graph)

    @classmethod
    def from_perf_script_data(
        cls, perf_script: PerfScriptData, pid: int | None = None, cpu: int | None = None
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
        node_table = NodeTable.from_perf_script_data(perf_script, pid=pid, cpu=cpu)
        directed_graph = nx.DiGraph()

        for block in perf_script.blocks:
            calls = block.calls
            for i in range(1, len(calls)):
                caller = calls[i - 1].addr
                callee = calls[i].addr
                directed_graph.add_edge(
                    node_table[callee], node_table[caller], weight=1
                )

        return cls(directed_graph=directed_graph, node_table=node_table)

    def show(self):
        """
        Displays the call graph.

        Returns:
            None
        """
        nx.draw(self.directed_graph, with_labels=True)
        plt.show()

    def save(self, file_path: str):
        """
        Saves the call graph to a file.

        Args:
            file_path (str): The path to save the call graph.

        Returns:
            None
        """
        nx.write_gexf(self.directed_graph, file_path)
