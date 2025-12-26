# -*- coding: utf-8 -*-
"""PIPA MCP server assembly.

This module builds a shared FastMCP instance and registers all tool groups.
"""
from __future__ import annotations

from fastmcp import FastMCP

from .tools.flamegraph import register_flamegraph_tools


def build_mcp(name: str = "pipa-mcp") -> FastMCP:
    mcp = FastMCP(name=name)
    register_flamegraph_tools(mcp)
    return mcp


mcp = build_mcp()

__all__ = ["mcp", "build_mcp"]
