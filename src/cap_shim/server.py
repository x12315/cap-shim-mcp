"""MCP 协议处理：JSON-RPC 消息分发，与传输层无关。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: Callable[[dict], str]  # sync: arguments -> result text


@dataclass
class MCPServer:
    name: str
    version: str
    tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def handle_message(self, raw: bytes | str | dict) -> str | None:
        """Handle one JSON-RPC message.

        Returns JSON string to write back, or None for notifications.
        """
        if isinstance(raw, dict):
            msg = raw
        else:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                return None

        method = msg.get("method")
        msg_id = msg.get("id")
        params = msg.get("params", {})

        if method == "initialize":
            return self._rpc(msg_id, self._init_result())
        elif method == "notifications/initialized":
            return None
        elif method == "tools/list":
            return self._rpc(msg_id, {"tools": self._tool_defs()})
        elif method == "tools/call":
            return self._rpc(msg_id, self._tool_result(params))
        else:
            return self._rpc(msg_id, {})

    # ---- helpers ----

    def _init_result(self) -> dict:
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": self.name, "version": self.version},
        }

    def _tool_defs(self) -> list[dict]:
        return [
            {"name": t.name, "description": t.description, "inputSchema": t.input_schema}
            for t in self.tools.values()
        ]

    def _tool_result(self, params: dict) -> dict | dict[str, Any]:
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        tool = self.tools.get(tool_name)
        if not tool:
            return _error(-32601, f"Unknown tool: {tool_name}")

        try:
            text = tool.handler(arguments)
            return {"content": [{"type": "text", "text": text}]}
        except Exception as exc:
            return _error(-32603, str(exc))

    @staticmethod
    def _rpc(msg_id: Any, result: dict | None = None) -> str:
        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": msg_id}
        if isinstance(result, dict) and "error" in result and "code" in result.get("error", {}):
            payload["error"] = result["error"]
        else:
            payload["result"] = result or {}
        return json.dumps(payload, ensure_ascii=False)


def _error(code: int, message: str) -> dict:
    return {"error": {"code": code, "message": message}}
