# PIPA MCP 服务指南

## 启动服务器

```bash
PYTHONPATH=src python -m pipa.service.mcp --host 0.0.0.0 --port 8000 --path /mcp
```

- 服务名称：`pipa-mcp`
- 传输：streamable-http
- 端点：`http://<host>:<port><path>`

## 客户端示例
```bash
PYTHONPATH=src python script/mcp_client.py data/out.stacks-folded --url http://127.0.0.1:8000/mcp --topk-symbols 5 --topk-stacks 3
# 仅列出工具
PYTHONPATH=src python script/mcp_client.py --list-tools --url http://127.0.0.1:8000/mcp
```

## 已注册能力与示例（flamegraph）

> 公共参数：`order` 可选 `inclusive|leaf`；`topk_symbols/topk_stacks/limit` 为非负整数；路径要求可读文件。

- `analyze_folded_file`
  - 作用：读取折叠栈文件并返回 Top 符号/栈，含百分比。
  - 输入示例：
    ```json
    {"path": "data/out.stacks-folded", "topk_symbols": 3, "topk_stacks": 2, "order": "inclusive"}
    ```
  - 输出示例（节选）：
    ```json
    {
      "total_weight": 562180916,
      "top_symbols": [{"symbol": "entry_SYSCALL_64_after_hwframe", "inclusive": 206394607, "inclusive_pct": 36.71, ...}],
      "top_stacks": [{"stack": "swapper;...;intel_idle", "weight": 72904864, "weight_pct": 12.97}]
    }
    ```

- `analyze_folded_text`
  - 作用：直接对折叠栈文本（行形式）做 Top 摘要。
  - 输入示例：`{"text": "proc;f1;f2 10\nproc;f1;f3 5"}`
  - 输出要点：同上，`total_weight/top_symbols/top_stacks`。

- `collapse_perf_script`
  - 作用：将 `perf script` 输出折叠为映射，并返回若干行示例。
  - 输入示例：
    ```json
    {"path": "data/perf_script_file.txt", "include_pid": false, "include_tid": false, "limit": 5}
    ```
  - 输出要点：`total_weight`、`unique_stacks`、`lines`（至多 `limit` 行，形如 `proc;f1;... weight`）。

- `symbol_overhead`
  - 作用：Trie 查询指定符号的开销，可模糊匹配，支持深度限制。
  - 输入示例：`{"path": "data/out.stacks-folded", "symbol": "main", "depth": 1, "fuzzy": true}`
  - 输出要点：`total`、`results` 列表（含 `inclusive/leaf` 及百分比，`path` 为匹配路径）。

- `export_call_tree`
  - 作用：导出加权排序的调用树，可指定起始符号、深度、模糊。
  - 输入示例：`{"path": "data/out.stacks-folded", "start_symbol": null, "depth": 1}`
  - 输出要点：`trees` 为节点数组，节点含 `name/count/leaf_count/children`（已按 count 降序）。

- `subset_analyze`
  - 作用：按符号取子集后做 Top 摘要。
  - 输入示例：`{"path": "data/out.stacks-folded", "symbol": "main", "topk_symbols": 4, "topk_stacks": 3}`
  - 输出要点：同 `analyze_folded_file`，但仅子集。

- `analyze_folded_lines`
  - 作用：对折叠行迭代器做摘要（自动化/流水线场景）。
  - 输入示例：`{"lines": ["proc;a;b 3", "proc;a;c 2"]}`
  - 输出要点：同 Top 摘要。

- `folded_text_to_trie`
  - 作用：折叠文本转 Trie，并导出树。
  - 输入示例：`{"text": "proc;a;b 3\nproc;a;c 2", "depth": 2}`
  - 输出要点：`total`、`trees`（结构同 `export_call_tree`）。

## 本地测试

```bash
PYTHONPATH=src /home/xyjiang/.conda/envs/311/bin/python -m pytest test/test_mcp_flamegraph.py
```
（其中 `data/out.stacks-folded`、`data/perf_script_file.txt` 存在时执行完整用例；缺失会 skip 部分。）
