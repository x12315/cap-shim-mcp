# MCP Servers — Agent 通用能力包

> 图片识别 (Qwen-VL) + 联网搜索 (Tavily)，所有 agent 共用。
> 适配: **Claude Code / Codex / Reasonix** 及任何支持 MCP 的 agent。

## 快速开始

```bash
cd codex-mcp-migration
./setup.sh
```

部署后文件结构:

```
~/.mcp-servers/
├── .env              ← API Keys (chmod 600, git ignore)
├── vision/
│   └── server.py     ← 图片识别 (Qwen-VL-Max)
├── search/
│   └── server.py     ← 联网搜索 (Tavily)
└── deploy.sh
```

## API Keys

全部集中在 `~/.mcp-servers/.env`，一处管理:

```bash
DASHSCOPE_API_KEY=sk-xxx    # 阿里云 DashScope → https://dashscope.console.aliyun.com
TAVILY_API_KEY=tvly-xxx     # Tavily Search → https://app.tavily.com
```

server.py 通过 stdlib `_load_env()` 读取，无需 pip 安装任何依赖。

## 注册到 Agent

### Reasonix

追加到 `~/.reasonix/config.toml`（全局）或项目 `reasonix.toml` 的 `[[plugins]]` 段：

```toml
[[plugins]]
name    = "qwen-vision"
command = "python3"
args    = ["/Users/montana/.mcp-servers/vision/server.py"]

[[plugins]]
name    = "tavily-search"
command = "python3"
args    = ["/Users/montana/.mcp-servers/search/server.py"]
```

### Claude Code / 其他 agent

```json
{
  "mcpServers": {
    "vision-mcp": {
      "command": "python3",
      "args": ["/Users/montana/.mcp-servers/vision/server.py"]
    },
    "search-mcp": {
      "command": "python3",
      "args": ["/Users/montana/.mcp-servers/search/server.py"]
    }
  }
}
```

## 设计原则

- **Zero deps**: stdlib only，不依赖 pip/venv
- **Agent 无关**: 不绑定特定 agent，路径用绝对路径
- **API Keys 集中**: `.env` + `chmod 600` + `.gitignore`

## 故障排查

| 现象 | 检查 |
|:-----|:----|
| MCP 工具未出现 | 确认 agent config 中路径为绝对路径（不要用 `~`） |
| 调用报 Key 错误 | 检查 `~/.mcp-servers/.env` 是否存在且 key 正确 |
| 图片分析无响应 | `DASHSCOPE_API_KEY` 是否有效，额度是否用完 |
