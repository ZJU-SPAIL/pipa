# PIPA MCP 服务指南

## 启动服务器

```bash
PYTHONPATH=src python -m pipa.service.mcp --host 0.0.0.0 --port 8000 --path /mcp
```

- 服务名称：`pipa-mcp`
- 传输：streamable-http
- 端点：`http://<host>:<port><path>`

## 客户端示例（覆盖 examples 所需链路）
```bash
# 列出已注册工具
PYTHONPATH=src python script/mcp_client.py --list-tools --url http://127.0.0.1:8000/mcp

# 标准分析链路：已有 folded 文件
PYTHONPATH=src python script/mcp_client.py data/out.stacks-folded \
  --url http://127.0.0.1:8000/mcp \
  --topk-symbols 5 --topk-stacks 3

# 如果只有 perf script，先折叠再分析
PYTHONPATH=src python script/mcp_client.py data/perf.script \
  --url http://127.0.0.1:8000/mcp \
  --collapse-only --limit 5
```

## 工具一览（flamegraph）

> 公共约束：输入文件需服务端可读；`topk_symbols/topk_stacks/limit` 为非负整数；`order` 取 `inclusive|leaf`。

- `collapse_perf_script_impl`
  - 作用：将 `perf script` 折叠为 mapping，直接做一次摘要，并把折叠结果写到服务器路径供后续工具使用。
  - 输入示例：`{"path": "data/perf.script", "limit": 5, "include_pid": false, "include_tid": false}`
  - 输出要点：`folded_path`（服务器侧路径）、`summary`（同 analyze 摘要）、`total_weight`、`unique_stacks`、`lines`（至多 `limit` 行）、`total_lines`、`truncated`。

- `analyze_folded_file_impl`
  - 作用：对折叠栈文件做 Top 摘要；支持 proc 过滤、前后缀过滤。
  - 输入示例：`{"path": "data/out.stacks-folded", "topk_symbols": 3, "topk_stacks": 2, "order": "inclusive"}`
  - 输出要点：`total_weight`、`top_symbols`、`top_stacks`，均带百分比。

- `subset_analyze_impl`
  - 作用：按符号取子集（含 proc 过滤）后再做 Top 摘要。
  - 输入示例：`{"path": "data/out.stacks-folded", "symbol": "main", "topk_symbols": 4, "topk_stacks": 3}`
  - 输出要点：同 `analyze_folded_file_impl`，但针对子集。

- `symbol_overhead_impl`
  - 作用：Trie 查询符号开销，可模糊匹配，限制深度。
  - 输入示例：`{"path": "data/out.stacks-folded", "symbol": "main", "depth": 1, "fuzzy": true}`
  - 输出要点：`total`、`results` 列表（含 `inclusive/leaf`、百分比、`path`）。

- `path_stats_impl`
  - 作用：路径/前缀统计，输出按权重排序列表。
  - 输入示例：`{"path": "data/out.stacks-folded", "limit": 50}`
  - 输出要点：`paths`（含计数与百分比）、`truncated`。

## 示例 Prompt（面向 MCP 客户端）
- 直接摘要已有折叠栈：
  - “Call tool `analyze_folded_file_impl` with args {"path": "data/out.stacks-folded", "topk_symbols": 5, "topk_stacks": 3, "order": "inclusive"} and return the JSON result.”
- 先折叠 perf script 再摘要：
  - “Call `collapse_perf_script_impl` with {"path": "data/perf.script", "limit": 5, "topk_symbols": 5, "topk_stacks": 3}; use returned `folded_path` for any later calls.”
- 子集聚焦：
  - “Call `subset_analyze_impl` with {"path": "data/out.stacks-folded", "symbol": "rocksdb::DBImpl", "topk_symbols": 5, "topk_stacks": 5}.”
- 符号开销：
  - “Call `symbol_overhead_impl` with {"path": "data/out.stacks-folded", "symbol": "main", "depth": 2, "fuzzy": true}.”
- 路径统计：
  - “Call `path_stats_impl` with {"path": "data/out.stacks-folded", "limit": 50}.”

## 典型调用路径（对应 examples）
- 已有折叠文件：直接调用 `analyze_folded_file_impl` / `subset_analyze_impl` / `symbol_overhead_impl` / `path_stats_impl`。
- 只有 `perf script`：先用 `collapse_perf_script_impl` 折叠（会产出 `folded_path` 与摘要），后续工具使用该 `folded_path`。

## 本地测试

```bash
PYTHONPATH=src /home/xyjiang/.conda/envs/311/bin/python -m pytest test/test_mcp_flamegraph.py
```
（`data/out.stacks-folded`、`data/perf_script_file.txt` 存在时执行完整用例；缺失会 skip 部分。）
