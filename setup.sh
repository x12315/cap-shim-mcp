#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MCP_HOME="$HOME/.mcp-servers"

echo "=== cap-shim 部署 ==="

# 1. 安装 Python 包
echo "[1/3] 安装依赖..."
if command -v uv &>/dev/null; then
    cd "$SCRIPT_DIR"
    uv sync
else
    echo "⚠️  uv 未安装，请先安装: brew install uv"
    exit 1
fi

# 2. 部署 .env
echo "[2/3] 配置 API Keys..."
mkdir -p "$MCP_HOME"
if [ ! -f "$MCP_HOME/.env" ]; then
    if [ -f "$SCRIPT_DIR/.env" ]; then
        cp "$SCRIPT_DIR/.env" "$MCP_HOME/.env"
    fi
    chmod 600 "$MCP_HOME/.env" 2>/dev/null || true
    echo "⚠️  请编辑 $MCP_HOME/.env 填入真实 API Key"
else
    echo ".env 已存在，跳过"
fi

# 3. 验证
echo "[3/3] 验证..."
"$SCRIPT_DIR/.venv/bin/cap-shim" --help > /dev/null 2>&1
echo "  cap-shim ✓"

echo ""
echo "✓ 部署完成。用法:"
echo ""
echo "  本地 stdio:"
echo "    uv run cap-shim stdio vision"
echo "    uv run cap-shim stdio search"
echo ""
echo "  服务器 HTTP/SSE:"
echo "    uv run cap-shim serve vision --port 8080"
echo "    uv run cap-shim serve search --port 8081"
echo ""
echo "  注册到 Agent (stdio):"
echo "    {"
echo "      \"mcpServers\": {"
echo "        \"qwen-vision\": { \"command\": \"uv\", \"args\": [\"run\", \"cap-shim\", \"stdio\", \"vision\"] },"
echo "        \"tavily-search\": { \"command\": \"uv\", \"args\": [\"run\", \"cap-shim\", \"stdio\", \"search\"] }"
echo "      }"
echo "    }"
