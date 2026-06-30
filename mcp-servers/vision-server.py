#!/usr/bin/env python3
"""MCP server: vision via Qwen-VL. Zero deps (stdlib only)."""
import json, sys, base64, mimetypes, os
from pathlib import Path
from urllib.request import Request, urlopen

VISION_KEY = "YOUR_DASHSCOPE_KEY_HERE"
VISION_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
VISION_MODEL = "qwen-vl-max"
MAX_IMAGES = 5

def encode_image(path):
    path = Path(path).expanduser().resolve()
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode()
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    return b64, mime

def call_vision(images, prompt):
    content = [{"type": "text", "text": prompt or "Describe these images in detail."}]
    for b64, mime in images[:MAX_IMAGES]:
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
    body = json.dumps({
        "model": VISION_MODEL,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 4096,
    }).encode()
    req = Request(VISION_URL, data=body, headers={
        "Authorization": f"Bearer {VISION_KEY}",
        "Content-Type": "application/json",
    })
    resp = urlopen(req, timeout=60)
    return json.loads(resp.read())["choices"][0]["message"]["content"]

def rpc(id=None, result=None, error=None):
    resp = {"jsonrpc": "2.0", "id": id}
    if error: resp["error"] = {"code": -1, "message": str(error)}
    else: resp["result"] = result
    sys.stdout.write(json.dumps(resp) + "\n"); sys.stdout.flush()

for line in sys.stdin:
    msg = json.loads(line)
    m, i = msg.get("method"), msg.get("id")
    p = msg.get("params", {})
    if m == "initialize":
        rpc(i, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "qwen-vision", "version": "0.1"}})
    elif m == "notifications/initialized":
        pass
    elif m == "tools/list":
        rpc(i, {"tools": [{"name": "analyze_image", "description": "Analyze image(s). Provide local file paths or URLs.", "inputSchema": {"type": "object", "properties": {"images": {"type": "array", "items": {"type": "string"}, "description": "File paths or URLs"}, "prompt": {"type": "string", "description": "Optional question"}}, "required": ["images"]}}]})
    elif m == "tools/call":
        args = p.get("arguments", {})
        paths = args.get("images", [])
        prompt = args.get("prompt", "")
        try:
            encoded = [encode_image(p) for p in paths]
            result = call_vision(encoded, prompt)
            rpc(i, {"content": [{"type": "text", "text": result}]})
        except Exception as e:
            rpc(i, error=str(e))
