"""MCP 传输层：stdio 和 HTTP/SSE。"""

from __future__ import annotations

import asyncio
import json
import select
import sys

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from .server import MCPServer


# ---- stdio ----

def run_stdio(server: MCPServer, idle_timeout: int = 300) -> None:
    """stdio transport with idle timeout self-exit."""
    while True:
        ready, _, _ = select.select([sys.stdin], [], [], idle_timeout)
        if not ready:
            break
        line = sys.stdin.readline()
        if not line:
            break

        response = server.handle_message(line)
        if response is not None:
            sys.stdout.write(response + "\n")
            sys.stdout.flush()


# ---- HTTP/SSE ----

def create_http_app(server: MCPServer) -> Starlette:
    """Build Starlette app with MCP SSE endpoints."""

    async def sse_endpoint(request: Request) -> StreamingResponse:
        async def stream():
            yield b"event: endpoint\ndata: /message\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    async def message_endpoint(request: Request) -> JSONResponse:
        try:
            body = await request.body()
        except Exception:
            return JSONResponse({"error": "Cannot read body"}, status_code=400)

        try:
            msg = json.loads(body)
        except json.JSONDecodeError:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        response = await asyncio.to_thread(server.handle_message, msg)
        if response is None:
            return JSONResponse({})
        return JSONResponse(json.loads(response))

    return Starlette(routes=[
        Route("/sse", sse_endpoint, methods=["GET"]),
        Route("/message", message_endpoint, methods=["POST"]),
    ])


def run_http(server: MCPServer, host: str = "0.0.0.0", port: int = 8080) -> None:
    """Run MCP server over HTTP/SSE. Blocks forever."""
    import uvicorn
    app = create_http_app(server)
    uvicorn.run(app, host=host, port=port, log_level="info")
