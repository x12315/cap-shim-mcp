#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MCP_HOME="$HOME/.mcp-servers"

echo "=== cap-shim 部署 ==="

# 1. 安装 Python 包
echo "[1/4] 安装依赖..."
if command -v uv &>/dev/null; then
    cd "$SCRIPT_DIR"
    uv sync
else
    echo "⚠️  uv 未安装，请先安装: brew install uv"
    exit 1
fi

# 2. 部署 .env
echo "[2/4] 配置 API Keys..."
mkdir -p "$MCP_HOME"
if [ ! -f "$MCP_HOME/.env" ]; then
    if [ -f "$SCRIPT_DIR/config/env.template" ]; then
        cp "$SCRIPT_DIR/config/env.template" "$MCP_HOME/.env"
    fi
    chmod 600 "$MCP_HOME/.env" 2>/dev/null || true
    echo "⚠️  请编辑 $MCP_HOME/.env 填入真实 API Key"
else
    echo ".env 已存在，跳过"
fi

# 3. 生成 Agent 配置
echo "[3/4] 生成 OpenCode 配置..."
if [ ! -f "$SCRIPT_DIR/opencode.jsonc" ]; then
  if [ -f "$SCRIPT_DIR/config/opencode.jsonc.example" ]; then
    sed "s|/path/to/cap-shim-mcp|$SCRIPT_DIR|g" \
      "$SCRIPT_DIR/config/opencode.jsonc.example" > "$SCRIPT_DIR/opencode.jsonc"
    echo "  opencode.jsonc 已生成 (proxy 模式)"
  fi
else
  echo "  opencode.jsonc 已存在，跳过"
fi

# 4. 验证
echo "[4/4] 验证..."
"$SCRIPT_DIR/.venv/bin/cap-shim" --help > /dev/null 2>&1
echo "  cap-shim ✓"

echo ""
echo "✓ 部署完成。用法:"
echo ""
echo "  启动后端服务（需在 OpenCode 启动前运行）:"
echo "    uv run cap-shim serve vision --port 8080 &"
echo "    uv run cap-shim serve search --port 8081 &"
echo ""
echo "  或者用 launchd 永久化（macOS）:"
echo "    cp deploy/launchd/*.plist ~/Library/LaunchAgents/"
echo "    launchctl load ~/Library/LaunchAgents/cap-shim.*.plist"
echo ""
echo "  远程服务器（可选）:"
echo "    服务器上 systemd 部署，本地 .env 加 PROXY_REMOTE_HOST=IP"
echo ""
echo "  OpenCode 配置已写入 opencode.jsonc (proxy 模式)"
