"""CLI 入口：cap-shim serve|stdio vision|search [--port PORT]"""

from __future__ import annotations

import argparse
import atexit
import os
import signal
import sys
import time
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

PROXY_PID_FILE = os.environ.get("CAP_SHIM_PROXY_PID", "/tmp/cap-shim-proxy.pid")


def _kill_old_proxy() -> None:
    try:
        with open(PROXY_PID_FILE) as f:
            old_pid = int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return
    if old_pid == os.getpid():
        return
    try:
        os.kill(old_pid, signal.SIGTERM)
        for _ in range(20):
            try:
                os.kill(old_pid, 0)
                time.sleep(0.1)
            except ProcessLookupError:
                break
        else:
            os.kill(old_pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _write_pid() -> None:
    # 原子创建 PID 文件，防止竞态
    fd = os.open(PROXY_PID_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    try:
        os.write(fd, str(os.getpid()).encode())
    finally:
        os.close(fd)


def _cleanup_pid() -> None:
    try:
        os.remove(PROXY_PID_FILE)
    except FileNotFoundError:
        pass


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

    args = parser.parse_args()

    if args.command == "proxy":
        try:
            _kill_old_proxy()
            try:
                os.remove(PROXY_PID_FILE)
            except FileNotFoundError:
                pass
            _write_pid()
            atexit.register(_cleanup_pid)
            server = create_proxy()
            transports.run_stdio(server, idle_timeout=args.idle_timeout)
        except FileExistsError:
            sys.exit(0)
        except Exception:
            traceback.print_exc()
            import datetime as _dt
            with open("/tmp/cap-shim-proxy-crash.log", "a") as _f:
                _f.write(f"\n[{_dt.datetime.now()}]\n")
                traceback.print_exc(file=_f)
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
