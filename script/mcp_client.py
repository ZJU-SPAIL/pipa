# -*- coding: utf-8 -*-
"""Simple MCP client for the pipa MCP streamable HTTP server."""
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from mcp import ClientSession, types
from mcp.client.streamable_http import streamable_http_client


def _render_call_result(result: Any) -> str:
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return json.dumps(structured, ensure_ascii=False, indent=2)
    parts = []
    for content in getattr(result, "content", []) or []:
        if isinstance(content, types.TextContent):
            parts.append(content.text)
        else:
            parts.append(repr(content))
    if parts:
        return "\n".join(parts)
    return repr(result)


async def run_client(args: argparse.Namespace) -> None:
    async with streamable_http_client(args.url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            if args.list_tools:
                print("Available tools:")
                for t in tools.tools:
                    print(f"- {t.name}: {t.description}")
                return
            if not args.path:
                raise SystemExit("--path is required unless --list-tools is used")
            payload = {
                "path": args.path,
                "topk_symbols": args.topk_symbols,
                "topk_stacks": args.topk_stacks,
                "order": args.order,
            }
            result = await session.call_tool("analyze_folded_file", arguments=payload)
            print(_render_call_result(result))


def main() -> None:
    parser = argparse.ArgumentParser(description="MCP client for pipa MCP server")
    parser.add_argument(
        "path", nargs="?", help="Path to folded stack file for analysis"
    )
    parser.add_argument(
        "--url", default="http://localhost:8000/mcp", help="MCP server URL"
    )
    parser.add_argument(
        "--topk-symbols", type=int, default=10, help="Number of top symbols"
    )
    parser.add_argument(
        "--topk-stacks", type=int, default=5, help="Number of top stacks"
    )
    parser.add_argument("--order", choices=["inclusive", "leaf"], default="inclusive")
    parser.add_argument(
        "--list-tools", action="store_true", help="Only list server tools"
    )
    args = parser.parse_args()
    asyncio.run(run_client(args))


if __name__ == "__main__":
    main()
