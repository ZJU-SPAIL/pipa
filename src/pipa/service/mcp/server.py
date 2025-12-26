# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse

from . import mcp


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run PIPA MCP server (streamable HTTP)"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Listen host")
    parser.add_argument("--port", type=int, default=8000, help="Listen port")
    parser.add_argument("--path", default="/mcp", help="HTTP path for MCP")
    args = parser.parse_args()
    mcp.run(transport="streamable-http", host=args.host, port=args.port, path=args.path)


if __name__ == "__main__":
    main()
