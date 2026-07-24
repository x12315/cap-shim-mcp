"""CLI 入口：mcp-hub serve|stdio vision|search [--port PORT]"""

from __future__ import annotations

import argparse

from . import config, transports
from .vision import create_server as create_vision
from .search import create_server as create_search

SERVERS = {
    "vision": create_vision,
    "search": create_search,
}

DEFAULT_PORTS = {
    "vision": config.VISION_PORT,
    "search": config.SEARCH_PORT,
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="mcp-hub", description="MCP Hub — 通用 MCP 工具集")
    sub = parser.add_subparsers(dest="command", required=True)

    # serve
    p_serve = sub.add_parser("serve", help="以 HTTP/SSE 模式启动")
    p_serve.add_argument("server", choices=list(SERVERS))
    p_serve.add_argument("--port", type=int, default=None)
    p_serve.add_argument("--host", default="0.0.0.0")

    # stdio
    p_stdio = sub.add_parser("stdio", help="以 stdio 模式启动")
    p_stdio.add_argument("server", choices=list(SERVERS))
    p_stdio.add_argument("--idle-timeout", type=int, default=300)

    args = parser.parse_args()

    server = SERVERS[args.server]()

    if args.command == "stdio":
        transports.run_stdio(server, idle_timeout=args.idle_timeout)
    elif args.command == "serve":
        port = args.port or DEFAULT_PORTS[args.server]
        transports.run_http(server, host=args.host, port=port)


if __name__ == "__main__":
    main()
