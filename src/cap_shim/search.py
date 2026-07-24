"""联网搜索 MCP 工具：Tavily Search API。"""

from __future__ import annotations

import json
from urllib.request import Request, urlopen

from . import config
from .server import MCPServer, Tool


def do_search(query: str, max_results: int = 5) -> str:
    if not query:
        raise ValueError("query 参数不能为空")

    body = json.dumps({
        "api_key": config.TAVILY_API_KEY,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
    }).encode()

    req = Request(config.TAVILY_URL, data=body, headers={"Content-Type": "application/json"})
    resp = urlopen(req, timeout=30)
    data = json.loads(resp.read())
    results = data.get("results", [])

    out = [
        f"{r.get('title', '')}\n{r.get('url', '')}\n{r.get('content', '')}"
        for r in results[:max_results]
    ]
    return "\n---\n".join(out) if out else "No results."


def _handle_web_search(args: dict) -> str:
    return do_search(
        args.get("query", ""),
        args.get("max_results", 5),
    )


def create_server() -> MCPServer:
    srv = MCPServer(name="tavily-search", version="0.5")
    srv.register(Tool(
        name="web_search",
        description="Search the web for current information.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {
                    "type": "integer",
                    "description": "Max results (1-10)",
                },
            },
            "required": ["query"],
        },
        handler=_handle_web_search,
    ))
    return srv
