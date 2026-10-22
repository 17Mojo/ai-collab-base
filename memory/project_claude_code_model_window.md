---
name: Claude Code 对未注册自定义模型按 200k 上下文窗口假设
description: 模型 ID 为 MiniMax-M3.1-Flash 等未在 Claude Code 注册表内的自定义模型时，报 unrecognized_model 并按 200k 窗口计算；属噪音告警而非任务失败
type: project
from: Agent
---

在本项目使用 `MiniMax-M3.1-Flash` 这类**未在 Claude Code 模型注册表中登记的自定义模型 ID** 时，Claude Code（实测版本 **2.1.302**）会输出告警：

```text
Claude Code doesn't recognize the model "MiniMax-M3.1-Flash", so it assumes a context window of 200k tokens.
[claude-code:unrecognized_model] {"model":"MiniMax-M3.1-Flash","query_source":"sdk"}
```

- 该告警**与任务成败无关**：2026-10-22 同一次调用退出码 0 且输出正确。
- 后果是**上下文窗口按 200k 假设**，长上下文/大文件任务可能被提前截断。

**Why**: 走自定义模型 ID 或网关时 Claude Code 无法查表，窗口大小由官方默认值兜底；不显式声明就只能拿到保守值。

**How to apply**: 看到 `unrecognized_model` 不要判为任务失败或去改业务代码；要精确窗口时按官方文档 `https://code.claude.com/docs/en/model-config#correct-the-window-for-a-gateway-or-custom-model-id` 在模型配置中显式声明。在长上下文任务前先确认实际窗口假设值，必要时拆小任务。
