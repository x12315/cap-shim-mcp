"""MCP proxy: 探测后端服务可用性并自动路由工具调用。"""

from __future__ import annotations

import json
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from . import config
from .server import MCPServer, Tool


_LOCAL = "http://127.0.0.1"


def _remote_url(port: int) -> str | None:
    if config.PROXY_REMOTE_HOST:
        return f"http://{config.PROXY_REMOTE_HOST}:{port}/call"
    return None


REGISTRY: dict[str, list[str]] = {
    "analyze_image": [b for b in [
        f"{_LOCAL}:{config.VISION_PORT}/call",
        _remote_url(config.VISION_PORT),
    ] if b is not None],
    "web_search": [b for b in [
        f"{_LOCAL}:{config.SEARCH_PORT}/call",
        _remote_url(config.SEARCH_PORT),
    ] if b is not None],
}

TOOL_DEFS = {
    "analyze_image": {
        "name": "analyze_image",
        "description": "Analyze image(s) with auto-resize. Provide local file paths, URLs, or base64 data URIs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File paths, HTTP(S) URLs, or data:image/...;base64,... URIs",
                },
                "prompt": {"type": "string", "description": "Optional question"},
            },
            "required": ["images"],
        },
    },
    "web_search": {
        "name": "web_search",
        "description": "Search the web for current information.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "description": "Max results (1-10)"},
            },
            "required": ["query"],
        },
    },
}


def _probe(url: str, timeout: float = 0.3) -> bool:
    parsed = urlparse(url)
    try:
        sock = socket.create_connection((parsed.hostname, parsed.port), timeout=timeout)
        sock.close()
        return True
    except Exception:
        return False


def probe_all() -> dict[str, str]:
    active: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures: dict = {}
        for name, backends in REGISTRY.items():
            for url in backends:
                futures[ex.submit(_probe, url)] = (name, url)
        for fut in as_completed(futures):
            name, url = futures[fut]
            if fut.result() and name not in active:
                active[name] = url
    return active


def _forward(url: str, tool_name: str, arguments: dict) -> str:
    body = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }).encode()
    req = Request(url, data=body, headers={"Content-Type": "application/json"})
    resp = urlopen(req, timeout=30)
    data = json.loads(resp.read())
    if "error" in data:
        raise RuntimeError(data["error"].get("message", str(data["error"])))
    result = data.get("result", {})
    for c in result.get("content", []):
        if c.get("type") == "text":
            return c["text"]
    return json.dumps(result, ensure_ascii=False)


def create_proxy() -> MCPServer:
    active = probe_all()
    srv = MCPServer(name="cap-shim-proxy", version="0.5")

    for name, first_url in active.items():
        td = TOOL_DEFS.get(name)
        if not td:
            continue

        def make_handler(tool_name: str = name, cached: str = first_url) -> object:
            def handler(args: dict) -> str:
                backends = REGISTRY[tool_name]
                ordered = [cached] + [u for u in backends if u != cached]
                for url in ordered:
                    try:
                        return _forward(url, tool_name, args)
                    except Exception:
                        continue
                raise RuntimeError(f"所有后端不可用: {tool_name}")
            return handler

        srv.register(Tool(
            name=td["name"],
            description=td["description"],
            input_schema=td["inputSchema"],
            handler=make_handler(),
        ))

    return srv
