#!/usr/bin/env python3
"""MCP server: web search via Tavily. Zero deps (stdlib only)."""
import json, sys
from urllib.request import Request, urlopen

TAVILY_KEY = "YOUR_TAVILY_KEY_HERE"
TAVILY_URL = "https://api.tavily.com/search"

def do_search(query, max_results=5):
    body = json.dumps({"api_key": TAVILY_KEY, "query": query, "max_results": max_results, "search_depth": "basic"}).encode()
    req = Request(TAVILY_URL, data=body, headers={"Content-Type": "application/json"})
    resp = urlopen(req, timeout=30)
    data = json.loads(resp.read())
    results = data.get("results", [])
    out = [f"{r.get('title','')}\n{r.get('url','')}\n{r.get('content','')}" for r in results[:max_results]]
    return "\n---\n".join(out) if out else "No results."

def rpc(id=None, result=None, error=None):
    resp = {"jsonrpc": "2.0", "id": id}
    if error: resp["error"] = error
    else: resp["result"] = result
    sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n"); sys.stdout.flush()

for line in sys.stdin:
    msg = json.loads(line)
    m, i = msg.get("method"), msg.get("id")
    p = msg.get("params", {})
    if m == "initialize":
        rpc(i, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "tavily-search", "version": "0.1"}})
    elif m == "notifications/initialized":
        pass
    elif m == "tools/list":
        rpc(i, {"tools": [{"name": "web_search", "description": "Search the web for current information.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}, "max_results": {"type": "integer", "description": "Max results (1-10)"}}, "required": ["query"]}}]})
    elif m == "tools/call":
        args = p.get("arguments", {})
        try:
            result = do_search(args.get("query", ""), args.get("max_results", 5))
            rpc(i, {"content": [{"type": "text", "text": result}]})
        except Exception as e:
            rpc(i, error=str(e))
