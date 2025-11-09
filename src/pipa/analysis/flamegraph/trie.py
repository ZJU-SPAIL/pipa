# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Tuple, Callable, Any

# 复用 analyzer 中使用的分隔符；为避免循环依赖，重复定义常量
SEPARATOR = ";"


@dataclass
class TrieNode:
    """前缀树节点：
    - name: 当前帧/函数名
    - count: 该节点被访问（作为路径前缀）的累计计数（inclusive）
    - leaf_count: 以该节点为叶子的样本计数（leaf）
    - children: 子节点哈希表，key 为函数名，O(1) 近似查找
    """

    name: str
    count: int = 0
    leaf_count: int = 0
    children: Dict[str, "TrieNode"] = field(default_factory=dict)

    def get_or_create_child(self, name: str) -> "TrieNode":
        node = self.children.get(name)
        if node is None:
            node = TrieNode(name=name)
            self.children[name] = node
        return node


@dataclass
class Trie:
    """Trie 包装器，root 的 name 固定为 "root"。"""

    root: TrieNode = field(default_factory=lambda: TrieNode(name="root"))
    total: int = 0  # 所有样本权重之和

    @classmethod
    def from_collapsed(
        cls, collapsed: Mapping[str, int], separator: str = SEPARATOR
    ) -> "Trie":
        """
        由折叠栈映射构建 Trie。
        - key 形如："comm pid/tid;f1;f2;f3"
        - 第一段视为进程标识，其余是调用栈自根到叶的顺序（与 pipa 的 FoldedAnalyzer 保持一致）
        """
        trie = cls()
        for stack, weight in collapsed.items():
            if not stack:
                continue
            parts = stack.split(separator)
            if len(parts) < 2:
                # 没有符号帧，忽略
                continue
            # 跳过进程标识，直接从符号序列构建
            frames = parts[1:]
            trie._insert(frames, int(weight))
            trie.total += int(weight)
        return trie

    @classmethod
    def from_lines(cls, lines: Iterable[str], separator: str = SEPARATOR) -> "Trie":
        """从标准 folded 文本行构建，行格式：
        "proc;f1;f2;f3 count"
        """
        coll: Dict[str, int] = {}
        for raw in lines:
            s = raw.strip()
            if not s:
                continue
            try:
                # 从右往左找空格分隔计数，允许符号中包含空格
                idx = s.rfind(" ")
                if idx == -1:
                    # 无显式权重，默认为 1
                    key, val = s, 1
                else:
                    key, val = s[:idx], int(s[idx + 1 :])
                coll[key] = coll.get(key, 0) + int(val)
            except ValueError:
                # 行格式异常，跳过
                continue
        return cls.from_collapsed(coll, separator=separator)

    def _insert(self, frames: List[str], weight: int) -> None:
        node = self.root
        node.count += weight  # root 作为总计数承载
        for i, name in enumerate(frames):
            node = node.get_or_create_child(name)
            node.count += weight
            if i == len(frames) - 1:
                node.leaf_count += weight

    # -----------------------
    # 基础遍历与统计工具
    # -----------------------
    def _sum_subtree_leaf_within_depth(
        self, node: TrieNode, max_depth: Optional[int]
    ) -> int:
        """在 node 子树内，统计距离 node 深度<=max_depth 的叶子权重之和。
        - max_depth is None 表示不限制深度，直接返回 node.count（等价于全部叶子之和）
        - max_depth == 0 表示仅 node 自身作为叶子的计数（即 node.leaf_count）
        - max_depth >= 1 表示向下继续累加
        """
        if max_depth is None:
            return node.count
        if max_depth < 0:
            return 0
        if max_depth == 0:
            return node.leaf_count
        total = node.leaf_count
        for child in node.children.values():
            total += self._sum_subtree_leaf_within_depth(child, max_depth - 1)
        return total

    def _find_nodes(
        self, predicate: Callable[[str], bool]
    ) -> List[Tuple[TrieNode, List[str]]]:
        """查找满足条件的节点，返回 (node, path) 列表，path 不含 root。"""
        results: List[Tuple[TrieNode, List[str]]] = []
        path: List[str] = []

        def dfs(n: TrieNode) -> None:
            if n is not self.root:
                path.append(n.name)
                if predicate(n.name):
                    results.append((n, path.copy()))
            for c in n.children.values():
                dfs(c)
            if n is not self.root:
                path.pop()

        for c in self.root.children.values():
            dfs(c)
        return results

    # 导出接口（路径列表）
    def iter_paths(self) -> Iterable[Tuple[List[str], int]]:
        """深度优先遍历，返回（路径, 叶子计数）。路径不含 root。"""
        path: List[str] = []

        def dfs(n: TrieNode) -> None:
            if n is not self.root:
                path.append(n.name)
                if n.leaf_count:
                    yield_tuple = (path.copy(), n.leaf_count)
                    results.append(yield_tuple)
            for child in n.children.values():
                dfs(child)
            if n is not self.root:
                path.pop()

        results: List[Tuple[List[str], int]] = []
        dfs(self.root)
        return results

    def to_path_stats(self) -> List[Tuple[str, int, float]]:
        """返回列表[("f1;f2;f3", count, percent)]，percent 为相对总样本的百分比[0,100]。"""
        total = self.total if self.total > 0 else 1
        out: List[Tuple[str, int, float]] = []
        for frames, cnt in self.iter_paths():
            pct = (cnt / total) * 100.0
            out.append((SEPARATOR.join(frames), cnt, pct))
        out.sort(key=lambda x: x[1], reverse=True)
        return out

    def to_symbol_stats(self) -> List[Tuple[str, int, int, float, float]]:
        """聚合到单符号维度，返回 [(symbol, inclusive, leaf, inclusive_pct, leaf_pct)]"""
        total = self.total if self.total > 0 else 1
        acc: Dict[str, Tuple[int, int]] = {}

        def dfs(n: TrieNode) -> None:
            inc, leaf = acc.get(n.name, (0, 0))
            inc += n.count
            leaf += n.leaf_count
            acc[n.name] = (inc, leaf)
            for c in n.children.values():
                dfs(c)

        for c in self.root.children.values():
            dfs(c)
        results: List[Tuple[str, int, int, float, float]] = []
        for sym, (inc, leaf) in acc.items():
            results.append(
                (sym, inc, leaf, (inc / total) * 100.0, (leaf / total) * 100.0)
            )
        results.sort(key=lambda x: (x[1], x[2]), reverse=True)
        return results

    # -----------------------
    # 查询接口：精确/模糊 + 深度限制 k
    # -----------------------
    def query_symbol_overhead(
        self, symbol: str, k: Optional[int] = None, fuzzy: bool = False
    ) -> List[Dict[str, Any]]:
        """查询某个 symbol（或包含该子串的 symbol）节点下的开销（overhead）。
        - k: 限制在该节点向下的最大深度（以边计），k=None 表示不限；k=0 仅统计该节点作为叶子本身。
        - 返回按 overhead(desc) 排序的结果列表：
          [{symbol, path, inclusive, leaf, inclusive_pct, leaf_pct}]
        说明：inclusive 此处表示在深度限制 k 内的叶子权重之和；leaf 为节点本身的 leaf_count。
        百分比以整棵 Trie 的 total 为分母。
        """
        if not symbol:
            return []

        def _predicate(name: str) -> bool:
            if fuzzy:
                return symbol in name
            return name == symbol

        matches = self._find_nodes(_predicate)
        if not matches:
            return []
        denom = self.total if self.total > 0 else 1
        rows: List[Dict[str, Any]] = []
        for node, path in matches:
            inclusive_k = self._sum_subtree_leaf_within_depth(node, k)
            leaf = node.leaf_count
            rows.append(
                {
                    "symbol": node.name,
                    "path": path,  # path 从根符号开始
                    "inclusive": inclusive_k,
                    "leaf": leaf,
                    "inclusive_pct": (inclusive_k / denom) * 100.0,
                    "leaf_pct": (leaf / denom) * 100.0,
                }
            )
        rows.sort(key=lambda r: r["inclusive"], reverse=True)
        return rows

    # -----------------------
    # 导出排序后的树（重路径靠上/左），支持起始符号与深度限制
    # -----------------------
    def export_sorted_tree(
        self,
        start_symbol: Optional[str] = None,
        fuzzy: bool = False,
        k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """导出从某个起始符号（或其模糊匹配）为根的子树，
        子节点按 count 降序排列，使“越重”越靠前（左）。
        - start_symbol: None 表示从整棵树（root 的孩子集合）开始；否则从匹配到的一个或多个节点分别导出
        - k: 限制导出深度（以边计）；k=None 不限；k=0 只导出起始节点本身（不含子节点）
        - 返回：若 start_symbol 为 None，则返回整个森林的列表；否则返回匹配列表（可能多个）
        节点字段：{name, count, leaf_count, children: [...]}，children 已按 count 降序
        """

        def sort_children_by_count(node: TrieNode) -> List[TrieNode]:
            # 稳定排序：count desc，然后名称 asc 以获得确定性
            return sorted(node.children.values(), key=lambda n: (-n.count, n.name))

        def build(node: TrieNode, depth_left: Optional[int]) -> Dict[str, Any]:
            obj: Dict[str, Any] = {
                "name": node.name,
                "count": node.count,
                "leaf_count": node.leaf_count,
                "children": [],
            }
            if depth_left is not None and depth_left <= 0:
                return obj
            next_depth = None if depth_left is None else depth_left - 1
            for child in sort_children_by_count(node):
                obj["children"].append(build(child, next_depth))
            return obj

        if start_symbol is None:
            # 从整棵树导出（root 下的每个第一层符号作为起点）
            roots = [c for c in self.root.children.values()]
            roots.sort(key=lambda n: (-n.count, n.name))
            return [build(r, k) for r in roots]

        # 否则从匹配到的节点导出（可能多个）
        def _start_match(nm: str) -> bool:
            if fuzzy:
                return start_symbol in nm  # type: ignore[arg-type]
            return nm == start_symbol  # type: ignore[arg-type]

        matches = self._find_nodes(_start_match)
        if not matches:
            return []
        # 稳定排序：按节点 inclusive(desc) 再 name
        matches.sort(key=lambda it: (-it[0].count, it[0].name))
        return [build(node, k) for node, _ in matches]


# 便捷函数


def build_trie_from_collapsed(
    collapsed: Mapping[str, int], separator: str = SEPARATOR
) -> Trie:
    return Trie.from_collapsed(collapsed, separator)


def build_trie_from_file(path: str, separator: str = SEPARATOR) -> Trie:
    with open(path, "r", encoding="utf-8") as f:
        return Trie.from_lines(f)
