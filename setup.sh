#!/bin/bash
# Codex MCP 迁移一键部署脚本
# 使用: chmod +x setup.sh && ./setup.sh
set -e

echo "=== Codex MCP 能力补全部署 ==="
echo ""

# 1. 目标目录
MCP_DIR="$HOME/.codex/mcp-servers"
mkdir -p "$MCP_DIR"
cp "$(dirname "$0")/mcp-servers/vision-server.py" "$MCP_DIR/"
cp "$(dirname "$0")/mcp-servers/search-server.py" "$MCP_DIR/"
echo "[1/3] MCP server 已复制到 $MCP_DIR"

# 2. 检查 API Key 是否已填入
for f in "$MCP_DIR/vision-server.py" "$MCP_DIR/search-server.py"; do
    if grep -q "YOUR_KEY_HERE\|tvly-dev.*1Hpahn" "$f" 2>/dev/null; then
        echo "  ⚠️  $(basename $f) 请替换占位 API Key"
    fi
done

# 3. 追加 MCP 配置到 config.toml
CONFIG_TOML="$HOME/.codex/config.toml"
if ! grep -q "\[mcp_servers.vision-mcp\]" "$CONFIG_TOML" 2>/dev/null; then
    cat >> "$CONFIG_TOML" << 'TOML'

[mcp_servers.vision-mcp]
command = "python3"
args = ["REPLACE_WITH_YOUR_PATH/vision-server.py"]
startup_timeout_sec = 30

[mcp_servers.search-mcp]
command = "python3"
args = ["REPLACE_WITH_YOUR_PATH/search-server.py"]
startup_timeout_sec = 30
TOML
    # 替换占位符为实际路径
    sed -i '' "s|REPLACE_WITH_YOUR_PATH|$MCP_DIR|g" "$CONFIG_TOML"
    echo "[2/3] MCP 配置已追加到 config.toml"
else
    echo "[2/3] MCP 配置已存在，跳过"
fi

# 4. 追加 AGENTS 规则
AGENTS_MD="$HOME/AGENTS.md"
AGENTS_TARGET="$HOME/.codex/AGENTS.md"

# 确定目标文件（AGENTS.md 可能是软链接）
if [ -L "$HOME/.codex/AGENTS.md" ]; then
    TARGET=$(readlink -f "$HOME/.codex/AGENTS.md")
else
    TARGET="$AGENTS_MD"
fi

if [ -f "$TARGET" ] && ! grep -q "后端能力回退" "$TARGET" 2>/dev/null; then
    echo "" >> "$TARGET"
    cat "$(dirname "$0")/config/AGENTS-rules.md" >> "$TARGET"
    echo "[3/3] AGENTS 回退规则已追加"
else
    echo "[3/3] AGENTS 规则已存在或目标文件未找到，手动确认"
fi

echo ""
echo "✓ 部署完成。重启 Codex 后新开会话测试。"
