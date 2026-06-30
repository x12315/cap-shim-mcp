# Codex MCP 能力补全迁移包

> 在 DeepSeek 等第三方后端无法提供图片识别、联网搜索时自动回退至前端 MCP 工具。

## 文件结构

```
codex-mcp-migration/
├── README.md          ← 本文件
├── setup.sh           ← 一键部署脚本
├── mcp-servers/
│   ├── vision-server.py   ← 视觉 MCP (Qwen-VL)
│   └── search-server.py   ← 搜索 MCP (Tavily)
└── config/
    ├── mcp-config.toml    ← MCP 服务器注册 (追加到 config.toml)
    └── AGENTS-rules.md    ← 后端能力回退规则 (追加到 AGENTS.md)
```

## 迁移步骤

### 0. 前提

- macOS，已安装 Codex
- 目标机器可运行 `python3`（系统自带）
- 准备两个 API Key：
  - Qwen-VL (DashScope): 视觉识别 — https://dashscope.console.aliyun.com → 模型服务 → API-KEY 管理 → 创建
  - Tavily: 联网搜索 — https://app.tavily.com → Sign Up → API Keys
  - 两者均有免费额度：DashScope 新用户百万 token 免费、Tavily 每月 1000 次免费搜索

### 1. 部署 MCP Server

```bash
# 复制 MCP server 到统一目录
mkdir -p ~/.codex/mcp-servers
cp mcp-servers/vision-server.py ~/.codex/mcp-servers/
cp mcp-servers/search-server.py ~/.codex/mcp-servers/

# 填入 API Key → 替换占位符
# vision-server.py: 搜索 YOUR_DASHSCOPE_KEY_HERE
# search-server.py: 搜索 YOUR_TAVILY_KEY_HERE
```

### 2. 注册到 Codex config.toml

打开 `~/.codex/config.toml`，在文件末尾追加 `config/mcp-config.toml` 的内容：

```toml
[mcp_servers.vision-mcp]
command = "python3"
args = ["/Users/你的用户名/.codex/mcp-servers/vision-server.py"]
startup_timeout_sec = 30

[mcp_servers.search-mcp]
command = "python3"
args = ["/Users/你的用户名/.codex/mcp-servers/search-server.py"]
startup_timeout_sec = 30
```

> **注意**：把 `/Users/你的用户名/` 替换为实际用户名或使用 `~` 这种 shell 扩展符号在 `config.toml` 里不可用，使用 `$HOME` 也不行，必须写绝对路径。

### 3. 写入 AGENTS 回退规则

将 `config/AGENTS-rules.md` 中的 "[后端能力回退]" 规则追加到 `~/.codex/AGENTS.md` 或 `~/AGENTS.md`。

### 4. 验证

重启 Codex，新开会话：

1. **视觉测试**：发一张图片，agent 尝试后端 → 失败 → 调用 `analyze_image` MCP → 首次弹窗授权 → 返回图片描述。
2. **搜索测试**：问一个实时问题，agent 调用 `web_search` MCP → 首次弹窗授权 → 返回搜索结果。

### 5. 工作原理

```
用户发图片/提问
  ↓
Agent 尝试后端能力（可能失败 / 第三方 API 不支持）
  ↓
AGENTS.md 规则：后端失败 → MCP 工具
  ↓
analyze_image ⋮ web_search (MCP)
  ↓
Qwen-VL Vision API ⋮ Tavily Search API
```

## 故障排查

| 现象 | 检查 |
|:-----|:----|
| MCP 工具未出现 | `grep "mcp_servers" ~/.codex/config.toml` 确认注册 |
| 调用时报 Key 错误 | 检查 server.py 里的 API Key 是否已替换 |
| Agent 不调用 MCP 工具 | AGENTS.md 规则是否写入正确位置 |
