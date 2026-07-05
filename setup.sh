#!/bin/bash
# MCP Servers 一键部署 — agent 通用版
# 使用: chmod +x setup.sh && ./setup.sh
set -e
MCP_HOME="$HOME/.mcp-servers"
echo "=== MCP Servers 部署 ==="
mkdir -p "$MCP_HOME/vision" "$MCP_HOME/search"
cp "$(dirname "$0")/mcp-servers/vision-server.py" "$MCP_HOME/vision/server.py"
cp "$(dirname "$0")/mcp-servers/search-server.py" "$MCP_HOME/search/server.py"
chmod +x "$MCP_HOME/vision/server.py" "$MCP_HOME/search/server.py"
if [ ! -f "$MCP_HOME/.env" ]; then
    cp "$(dirname "$0")/.env.example" "$MCP_HOME/.env"
    chmod 600 "$MCP_HOME/.env"
    echo "⚠️  请编辑 $MCP_HOME/.env 填入真实 API Key"
else
    echo ".env 已存在，跳过"
fi
echo "✓ 部署完成。在各 agent 配置中注册路径:"
echo "  python3 $MCP_HOME/vision/server.py"
echo "  python3 $MCP_HOME/search/server.py"
