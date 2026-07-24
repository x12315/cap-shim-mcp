"""统一配置管理：环境变量 + .env 加载。"""

import os
from pathlib import Path


def _load_env() -> None:
    candidates = [
        Path(os.environ.get("CAP_SHIM_ENV_FILE", "")),
        Path.home() / ".mcp-servers" / ".env",
        Path.cwd() / ".env",
    ]
    for env_path in filter(Path.is_file, candidates):
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
        break


_load_env()

# ---- API keys ----
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

# ---- Vision ----
VISION_MODEL = "qwen-vl-max"
VISION_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
MAX_IMAGES = 5
MAX_DIM = 2048
MAX_FILE_KB = 2048
RETRIES = 2
RETRY_DELAY = 2.0  # seconds

# ---- Search ----
TAVILY_URL = "https://api.tavily.com/search"

# ---- Ports ----
VISION_PORT = int(os.environ.get("VISION_PORT", "8080"))
SEARCH_PORT = int(os.environ.get("SEARCH_PORT", "8081"))
