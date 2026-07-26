"""联网搜索 MCP 工具：Tavily Search API。"""

from __future__ import annotations

import json
import time
from urllib.error import HTTPError, URLError
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

    last_err = ""
    for attempt in range(1 + config.RETRIES):
        try:
            req = Request(config.TAVILY_URL, data=body, headers={"Content-Type": "application/json"})
            resp = urlopen(req, timeout=30)
            data = json.loads(resp.read())
            results = data.get("results", [])

            out = [
                f"{r.get('title', '')}\n{r.get('url', '')}\n{r.get('content', '')}"
                for r in results[:max_results]
            ]
            return "\n---\n".join(out) if out else "No results."

        except HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode()[:300]
                err_data = json.loads(err_body)
                err_body = err_data.get("message", err_body)
            except Exception:
                pass
            last_err = f"HTTP {e.code}: {err_body}"
        except URLError as e:
            last_err = str(e)
        except Exception as e:
            last_err = str(e)

        if attempt < config.RETRIES:
            time.sleep(config.RETRY_DELAY)

    raise RuntimeError(f"搜索 API 调用失败（{config.RETRIES + 1} 次尝试）: {last_err}")


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
