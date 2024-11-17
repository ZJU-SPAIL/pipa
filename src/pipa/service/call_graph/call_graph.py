from typing import Literal, Mapping, Optional
import networkx as nx
import json
import matplotlib.pyplot as plt
from pipa.parser.perf_buildid import PerfBuildidData
from pipa.parser.perf_script_call import PerfScriptData
from networkx.drawing.nx_pydot import write_dot
from collections import defaultdict

from .node import NodeTable
from .func_node import FunctionNodeTable, ClusterEncoder


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
        filter_none: bool = False,
        gen_epm: bool = False,
        perf_buildid: Optional[PerfBuildidData] = None,
        source_file_prefix: Optional[str] = None,
    ):
        """
        Creates a CallGraph object from performance script data.

        Args:
            perf_script (PerfScriptData): The performance script data.
            pid (int, optional): The process ID. Defaults to None.
            cpu (int, optional): The CPU ID. Defaults to None.
            filter_none (bool): Whether to filter out unknown functions. Defaults to False.
            gen_epm (bool): Whether to generate EPM. Defaults to False.
            perf_buildid (PerfBuildidData, optional): The buildid data. Defaults to None.
            source_file_prefix (str, optional): The prefix of source file. Defaults to None.

        Returns:
            CallGraph: The CallGraph object created from the performance script data.
        """
        if pids is not None:
            perf_script = perf_script.filter_by_pids(pids=pids)
        if cpus is not None:
            perf_script = perf_script.filter_by_cpus(cpus=cpus)

        node_table = NodeTable.from_perf_script_data(perf_script)
        block_graph = nx.DiGraph()

        buildid_list = {}
        if perf_buildid:
            buildid_list = perf_buildid.buildid_lists
        func_table = FunctionNodeTable.from_node_table(
            node_table,
            gen_epm=gen_epm,
            buildid_list=buildid_list,
            source_file_prefix=source_file_prefix,
        )
        func_graph = nx.DiGraph()

        for block in perf_script.blocks:
            calls = block.calls
            for i in range(1, len(calls)):
                if filter_none:
                    for j in range(i - 1, -1, -1):
                        if node_table[calls[j].addr].get_function_name() != "[unknown]":
                            caller = calls[j].addr
                            break
                else:
                    caller = calls[i - 1].addr
                callee = calls[i].addr

                if filter_none and (
                    node_table[caller].get_function_name() == "[unknown]"
                    or node_table[callee].get_function_name() == "[unknown]"
                ):
                    continue
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
