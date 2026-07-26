# OpenCode MCP 集成实践指南

## 架构事实

### 每个对话独立的 Sidecar

OpenCode 的 MCP 架构基于 Effect `Scope`，每个对话（session）拥有独立的 MCP State，`type: "local"` 会为每个对话独立 spawn 一个 sidecar 进程。

```
对话 A → MCP State A → sidecar A
对话 B → MCP State B → sidecar B
对话 C → MCP State C → sidecar C
```

**不要试图做跨对话的单例锁**——对话间会互相杀死对方的 sidecar，导致状态不断翻转。

### 状态机制

```
绿色 = "connected"   → client.connect() 成功，tools 已注册
红色 = "failed"      → client.onclose 触发（进程退出/stdin EOF/pipe 断开）
黄色 = "needs_auth"  → 仅 remote OAuth 场景
```

- **没有周期性健康检查**。状态只在 connect/onclose 事件时切换。
- `onclose` 对所有对话独立触发，一个对话的 sidecar 死掉不影响其他对话。

### 重连逻辑

`connect() / authenticate()` 重连时：新 client 先 connect → 设 status="connected" → 再 close 旧 client → 旧 client 的 onclose 因引用对比（`s.clients[name] !== client`）被自动忽略。

## Sidecar 设计准则

### 1. 不阻塞启动

`initialize` 和 `tools/list` 必须在超时窗口内响应。默认 30 秒，但启动越早响应越稳定。不要在网络探测、进程清理等操作上同步等待。

### 2. 快速启动探测

如果 sidecar 需要探测后端服务健康状态，用并发短超时（300ms 级），不要逐个串行。

### 3. 处理并发调用

MCP 客户端可能同时发送多个 `tools/call`。用线程池方式并发处理，避免单线程阻塞排队。

### 4. 响应所有消息

对不支持的 MCP 方法返回空结果 `{}` 而非无响应，避免客户端无限等待。

### 5. 不依赖外部网络起机

sidecar 启动不应依赖远程网络可达。如果后端服务分本地/远程，探测失败时 graceful degrade（空工具列表），而非崩溃。

## 后端服务托管

### macOS: launchd

- `~/Library/LaunchAgents/` + XML plist
- `RunAtLoad: true` + `KeepAlive: true`
- `ProgramArguments` 直接指向 venv 内二进制，不套 `uv run`
- 注意：`~/Desktop/` 有 macOS 沙箱限制，launchd 子进程无法访问

### Linux: systemd

- `~/.config/systemd/user/`
- `Restart: always` + `EnvironmentFile`

## 常见问题排查

| 现象 | 可能原因 | 解决 |
|------|---------|------|
| 对话 MCP 永远不可用 | sidecar 进程从未成功启动 | 检查 config.command 路径和权限 |
| 随机变红 | sidecar 偶尔崩溃或 OpenCode 内部重连 | 确保 sidecar 所有异常有 try/catch |
| 全部对话同时变红 | sidecar 被外部杀（pkill/crash） | 排查僵尸进程和信号处理 |
| 启动时卡住 | sidecar 启动阶段同步阻塞太久 | 并发化/缩短锁定逻辑 |
| 工具调用超时 | API 调用阻塞了响应循环 | 线程池并发处理 slow path |

## 调试命令

```bash
# 检查 sidecar 进程
ps aux | grep <binary> | grep -v grep

# 检查 MCP 服务健康
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | <sidecar-binary>

# 查看 OpenCode MCP 日志
grep "MCP" ~/.local/share/opencode/log/opencode.log | tail -20

# 查看 launchd 状态
launchctl list | grep <label>
```

## 版本信息

- OpenCode: 截至 2026-07 (dev 分支)
- MCP 协议: 2024-11-05
