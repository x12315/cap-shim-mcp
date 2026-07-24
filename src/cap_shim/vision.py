"""图片识别 MCP 工具：Qwen-VL via DashScope。

支持三种图片输入：
  - 本地文件路径（stdio 模式）
  - HTTP(S) URL
  - base64 data URI（远程 HTTP 模式）
"""

from __future__ import annotations

import base64
import io
import json
import mimetypes
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image

from . import config
from .server import MCPServer, Tool


# ---- image encoding ----

def encode_image(source: str) -> tuple[str, str]:
    """编码图片为 (base64_string, mime_type)。"""
    if source.startswith("data:"):
        header, b64 = source.split(",", 1)
        mime = header.split(":")[1].split(";")[0]
        return b64, mime

    if source.startswith("http://") or source.startswith("https://"):
        req = Request(source, headers={"User-Agent": "Mozilla/5.0"})
        data = urlopen(req, timeout=30).read()
        ext = source.rsplit(".", 1)[-1] if "." in source else "png"
        mime = f"image/{ext}"
        processed = _preprocess(data)
        b64 = base64.b64encode(processed).decode()
        return b64, mime if processed is data else "image/jpeg"

    fp = Path(source).expanduser().resolve()
    if not fp.is_file():
        raise FileNotFoundError(f"图片不存在: {fp}")
    data = fp.read_bytes()
    mime = mimetypes.guess_type(str(fp))[0] or "image/png"
    processed = _preprocess(data)
    b64 = base64.b64encode(processed).decode()
    return b64, mime if processed is data else "image/jpeg"


def _preprocess(data: bytes) -> bytes:
    """缩放大图并重压缩为 JPEG。无需处理则返回原始数据。"""
    size_kb = len(data) // 1024
    try:
        img = Image.open(io.BytesIO(data))
    except Exception:
        return data

    max_dim = max(img.size)
    if max_dim <= config.MAX_DIM and size_kb <= config.MAX_FILE_KB:
        return data

    if max_dim > config.MAX_DIM:
        img.thumbnail((config.MAX_DIM, config.MAX_DIM))

    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=30)
    return buf.getvalue()


# ---- API call ----

def call_vision(images: list[tuple[str, str]], prompt: str) -> str:
    """调用 Qwen-VL API，返回模型输出文本。"""
    content: list[dict] = [
        {"type": "text", "text": prompt or "Describe these images in detail."}
    ]
    for b64, mime in images[: config.MAX_IMAGES]:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}"},
        })

    body = json.dumps({
        "model": config.VISION_MODEL,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 4096,
    }).encode()

    last_err = ""
    for attempt in range(1 + config.RETRIES):
        try:
            req = Request(config.VISION_URL, data=body, headers={
                "Authorization": f"Bearer {config.DASHSCOPE_API_KEY}",
                "Content-Type": "application/json",
            })
            resp = urlopen(req, timeout=90)
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
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

    raise RuntimeError(f"视觉 API 调用失败（{config.RETRIES + 1} 次尝试）: {last_err}")


# ---- tool handler ----

def _handle_analyze_image(args: dict) -> str:
    paths = args.get("images", [])
    if not paths:
        raise ValueError("images 参数不能为空")
    prompt = args.get("prompt", "")
    encoded = [encode_image(p) for p in paths]
    return call_vision(encoded, prompt)


# ---- server factory ----

def create_server() -> MCPServer:
    srv = MCPServer(name="qwen-vision", version="0.5")
    srv.register(Tool(
        name="analyze_image",
        description="Analyze image(s) with auto-resize. Provide local file paths, URLs, or base64 data URIs.",
        input_schema={
            "type": "object",
            "properties": {
                "images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File paths, HTTP(S) URLs, or data:image/...;base64,... URIs",
                },
                "prompt": {
                    "type": "string",
                    "description": "Optional question",
                },
            },
            "required": ["images"],
        },
        handler=_handle_analyze_image,
    ))
    return srv
