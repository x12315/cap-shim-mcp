#!/usr/bin/env python3
"""MCP server: vision via Qwen-VL. Zero deps (stdlib only).

Reads DASHSCOPE_API_KEY from ~/.mcp-servers/.env (fallback: env var).
"""
import json, sys, base64, mimetypes, os
from pathlib import Path
from urllib.request import Request, urlopen

# ---- load .env (stdlib only): check multiple locations ----
def _load_env():
    candidates = [
        Path.home() / ".mcp-servers" / ".env",       # deployed
        Path(__file__).resolve().parent / ".env",    # same dir
        Path(__file__).resolve().parent.parent / ".env",  # parent dir
    ]
    for env_path in candidates:
        if not env_path.is_file():
            continue
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
        break  # use first found

_load_env()

VISION_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
VISION_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
VISION_MODEL = "qwen-vl-max"
MAX_IMAGES = 5

def encode_image(path):
    p = str(path)
    if p.startswith("http://") or p.startswith("https://"):
        req = Request(p, headers={"User-Agent": "Mozilla/5.0"})
        data = urlopen(req, timeout=30).read()
        mime = "image/" + (p.rsplit(".", 1)[-1] if "." in p else "png")
    else:
        fp = Path(p).expanduser().resolve()
        data = fp.read_bytes()
        mime = mimetypes.guess_type(str(fp))[0] or "image/png"
    b64 = base64.b64encode(data).decode()
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
    if error:
        resp["error"] = {"code": -1, "message": str(error)}
    else:
        resp["result"] = result
    sys.stdout.write(json.dumps(resp) + "\n")
    sys.stdout.flush()

for line in sys.stdin:
    msg = json.loads(line)
    m, i = msg.get("method"), msg.get("id")
    p = msg.get("params", {})
    if m == "initialize":
        rpc(i, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "qwen-vision", "version": "0.2"}})
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
