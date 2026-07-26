# cap-shim — capability shim for AI models

> 给 AI 模型补上后端能力：图片识别 (Qwen-VL) + 联网搜索 (Tavily)。
> 支持 **stdio** 和 **HTTP/SSE** 双传输层。适配任何支持 MCP 的 agent。

## 快速开始

```bash
git clone https://github.com/x12315/cap-shim-mcp.git
cd cap-shim-mcp
./setup.sh
```

## 两种运行模式

### 本地 stdio（Mac / 单机）

```bash
uv run cap-shim stdio vision
uv run cap-shim stdio search
```

Agent 配置参考 `.mcp.json`。

### 服务器 HTTP/SSE（家庭服务器 / 远程共享）

```bash
uv run cap-shim serve vision --port 8080
uv run cap-shim serve search --port 8081
```

部署到 systemd 参考 `deploy/systemd/`。

远程客户端配置（Claude Code / VS Code 等标准 MCP 客户端）：

```json
{
  "mcp": {
    "qwen-vision": { "transport": "sse", "url": "http://100.115.123.9:8080/sse" },
    "tavily-search": { "transport": "sse", "url": "http://100.115.123.9:8081/sse" }
  }
}
```

> **Open Code 不可用此配置**，请用上节 `local` + stdio 替代。详见下方「已知兼容性」。

## API Keys

全部集中在 `~/.mcp-servers/.env` 或项目根 `.env`：

```bash
QWEN_API_KEY=sk-xxx         # 阿里云 DashScope Qwen-VL
TAVILY_API_KEY=tvly-xxx     # Tavily Search → https://app.tavily.com
```

也可通过环境变量 `CAP_SHIM_ENV_FILE` 指定自定义路径。

## 图片输入支持

`analyze_image` 的 `images` 参数支持三种格式：

| 格式 | 示例 | 适用场景 |
|------|------|---------|
| 本地路径 | `/Users/.../screenshot.png` | stdio 模式 |
| HTTP URL | `https://example.com/a.jpg` | 通用 |
| base64 data URI | `data:image/jpeg;base64,/9j/...` | HTTP/SSE 远程模式 |

服务器端自动用 Pillow 对大图做缩放到 MAX_DIM (2048px) 和 JPEG 压缩。

## 目录结构

```
cap-shim-mcp/
├── src/cap_shim/           # Python 包
│   ├── config.py           # 统一配置
│   ├── server.py           # MCP 协议处理
│   ├── vision.py           # 图片识别
│   ├── search.py           # 联网搜索
│   ├── transports.py       # stdio + HTTP/SSE 传输层
│   └── cli.py              # CLI 入口
├── deploy/systemd/         # systemd unit 模板
├── setup.sh                # 本地一键部署
└── .mcp.json               # Agent 注册参考
```

## 部署到家庭服务器

```bash
# alpha (Arch Linux) 上
git clone https://github.com/x12315/cap-shim-mcp.git ~/cap-shim-mcp
cd ~/cap-shim-mcp
uv sync
cp config/env.template .env  # 编辑填入真实 key

# 安装 systemd user unit
mkdir -p ~/.config/systemd/user
cp deploy/systemd/*.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now mcp-vision mcp-search
```

## 已知兼容性

### Open Code 的 `remote` + SSE 已知缺陷

**症状**：Open Code 配置 `type: "remote"` + SSE URL 后，启动缓慢、历史对话空白、MCP 消息发送后立即终止。

**根因**：Open Code 对 MCP SSE 传输的实现存在已知 bug（[#3157](https://github.com/anomalyco/opencode/issues/3157)、[#834](https://github.com/anomalyco/opencode/issues/834)、[#232](https://github.com/anomalyco/opencode/issues/232)），remote SSE 握手失败会导致 sidecar 进程 `Die`，整个会话崩溃。

**解决方案**：使用 `local` + stdio，不走 SSE。

```jsonc
// opencode.jsonc — Open Code 全局配置
{
  "mcp": {
    "qwen-vision": {
      "type": "local",
      "command": ["uv", "run", "--directory", "/path/to/cap-shim-mcp", "cap-shim", "stdio", "vision"]
    },
    "tavily-search": {
      "type": "local",
      "command": ["uv", "run", "--directory", "/path/to/cap-shim-mcp", "cap-shim", "stdio", "search"]
    }
  }
}
```

> `remote` SSE 模式在其他客户端（Claude Code、VS Code MCP 扩展等）中工作正常。此问题仅影响 Open Code。

## 设计原则

- **传输层分离**: 核心逻辑不绑定 stdio 或 HTTP，同一份代码跑两种模式
- **跨平台**: Pillow 替代 macOS sips，Linux/Mac 通用
- **API Key 集中**: 一处管理，通过环境变量注入
- **零强制配置**: 开箱即用，所有参数有合理默认值
