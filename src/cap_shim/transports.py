"""MCP 传输层：stdio 和 HTTP/SSE。"""

from __future__ import annotations

import asyncio
import json
import select
import sys
import uuid

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from .server import MCPServer


# ---- stdio ----

import threading
from concurrent.futures import ThreadPoolExecutor

_stdout_lock = threading.Lock()


def run_stdio(server: MCPServer, idle_timeout: int = 300, max_workers: int = 4) -> None:
    """stdio transport with idle timeout self-exit (0 = no timeout).

    tools/call requests are dispatched to a thread pool so slow API
    calls do not block reading of subsequent messages.
    """
    executor = ThreadPoolExecutor(max_workers=max_workers)
    timeout = idle_timeout if idle_timeout > 0 else None

    def _write(response: str) -> None:
        with _stdout_lock:
            sys.stdout.write(response + "\n")
            sys.stdout.flush()

    def _handle_async(line: str) -> None:
        response = server.handle_message(line)
        if response is not None:
            _write(response)

    try:
        while True:
            ready, _, _ = select.select([sys.stdin], [], [], timeout)
            if not ready:
                break
            line = sys.stdin.readline()
            if not line:
                break

            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue

            method = msg.get("method")
            if method == "tools/call":
                executor.submit(_handle_async, line)
            else:
                response = server.handle_message(line)
                if response is not None:
                    _write(response)
    finally:
        executor.shutdown(wait=False)


# ---- HTTP/SSE ----

_SSE_IDLE_TIMEOUT = 600  # seconds


def _make_sse_event(data: str) -> bytes:
    return f"event: message\ndata: {data}\n\n".encode()


def create_http_app(server: MCPServer) -> Starlette:
    """Build Starlette app with MCP SSE endpoints (spec-compliant)."""
    sessions: dict[str, asyncio.Queue] = {}

    async def sse_endpoint(request: Request) -> StreamingResponse:
        session_id = uuid.uuid4().hex
        queue: asyncio.Queue = asyncio.Queue()
        sessions[session_id] = queue

        async def stream():
            try:
                yield f"event: endpoint\ndata: /message?sessionId={session_id}\n\n".encode()
                while True:
                    try:
                        data = await asyncio.wait_for(queue.get(), timeout=_SSE_IDLE_TIMEOUT)
                    except asyncio.TimeoutError:
                        break
                    if data is None:
                        break
                    yield data
            finally:
                sessions.pop(session_id, None)

        return StreamingResponse(stream(), media_type="text/event-stream")

    async def message_endpoint(request: Request) -> JSONResponse:
        session_id = request.query_params.get("sessionId", "")

        try:
            body = await request.body()
        except Exception:
            return JSONResponse({"error": "Cannot read body"}, status_code=400)

        try:
            msg = json.loads(body)
        except json.JSONDecodeError:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        response = await asyncio.to_thread(server.handle_message, msg)
        if response is not None and session_id:
            queue = sessions.get(session_id)
            if queue:
                await queue.put(_make_sse_event(response))

        return JSONResponse({}, status_code=202)

    async def health_endpoint(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "server": server.name, "version": server.version})

    async def call_endpoint(request: Request) -> JSONResponse:
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
        Route("/health", health_endpoint, methods=["GET"]),
        Route("/sse", sse_endpoint, methods=["GET"]),
        Route("/message", message_endpoint, methods=["POST"]),
        Route("/call", call_endpoint, methods=["POST"]),
    ])


def run_http(server: MCPServer, host: str = "0.0.0.0", port: int = 8080) -> None:
    """Run MCP server over HTTP/SSE. Blocks forever."""
    import uvicorn
    app = create_http_app(server)
    uvicorn.run(app, host=host, port=port, log_level="info")
