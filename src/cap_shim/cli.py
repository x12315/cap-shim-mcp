"""CLI 入口：cap-shim serve|stdio vision|search [--port PORT]"""

from __future__ import annotations

import argparse
import sys
import traceback

from . import config, transports
from .vision import create_server as create_vision
from .search import create_server as create_search
from .proxy import create_proxy

SERVERS = {
    "vision": create_vision,
    "search": create_search,
}

DEFAULT_PORTS = {
    "vision": config.VISION_PORT,
    "search": config.SEARCH_PORT,
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="cap-shim", description="cap-shim — capability shim for AI models")
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

    # proxy
    p_proxy = sub.add_parser("proxy", help="启动 proxy（自动探测并路由到可用后端）")
    p_proxy.add_argument("--idle-timeout", type=int, default=0)
    p_proxy.add_argument("--port", type=int, default=None, help="HTTP/SSE 模式端口（不指定则走 stdio）")
    p_proxy.add_argument("--host", default="0.0.0.0")

    args = parser.parse_args()

    if args.command == "proxy":
        try:
            server = create_proxy()
            if args.port:
                transports.run_http(server, host=args.host, port=args.port)
            else:
                transports.run_stdio(server, idle_timeout=args.idle_timeout)
        except Exception:
            traceback.print_exc()
            sys.exit(1)
    elif args.command == "stdio":
        server = SERVERS[args.server]()
        transports.run_stdio(server, idle_timeout=args.idle_timeout)
    elif args.command == "serve":
        server = SERVERS[args.server]()
        port = args.port or DEFAULT_PORTS[args.server]
        transports.run_http(server, host=args.host, port=port)


if __name__ == "__main__":
    main()
