# Copilot 回通知响应协议

## 触发检测

当 Copilot 检测到 `handoff_status.json` 中的 `status` 为 `RECEIVED_AND_PROCESSING` 时，触发以下响应：

---

## 📡 响应层级

### 层级 1：Claude（接收方）通知

```json
// 写入 claude_notification.json
{
  "from": "copilot",
  "to": "claude_code",
  "type": "handoff_acknowledged",
  "message": "✅ 交接已确认 - Claude 可继续工作",
  "handoff_id": "HANDOFF-20260226-NETWORK-RESEARCH",
  "timestamp": "2026-02-26T14:40:00.000Z",
  "next_action": "等待 Claude 完成工作后，可进入待命状态"
}
```

### 层级 2：用户通知（可选，非侵入式）

```json
// 写入 user_notification.json
{
  "type": "info",
  "title": "Copilot 网络调研完成",
  "message": "✅ 5 项技术选型调研已完成，Claude 正在处理结果",
  "details": {
    "completed_tasks": [
      "Chrome Manifest V3 最新规范",
      "国内 AI 网页 DOM 结构分析",
      "VS Code ↔ Chrome 通信方案",
      "OpenSpec 规范细节",
      "云函数平台对比"
    ],
    "results_file": "research/copilot-handoff/2026-02-26-copilot-to-claude.md",
    "current_status": "Claude 正在基于研究结果设计架构"
  },
  "action_required": false,
  "priority": "info"
}
```

### 层级 3：状态文件更新

```json
// 更新 handoff_status.json
{
  "handoff_id": "HANDOFF-20260226-NETWORK-RESEARCH",
  "from_ai": "copilot",
  "to_ai": "claude_code",
  "status": "HANDOFF_COMPLETE",
  "timeline": {
    "copilot_completed_at": "2026-02-26T14:30:00.000Z",
    "claude_received_at": "2026-02-26T14:35:00.000Z",
    "copilot_acknowledged_at": "2026-02-26T14:40:00.000Z"
  },
  "final_state": "CLAUDE_OWNS_TASK",
  "instructions": {
    "copilot": "进入待命状态，等待下一个任务分配",
    "claude": "交接流程完整，可继续架构设计和代码实现"
  }
}
```

---

## 🔄 完整交互流程

```
┌─────────────────────────────────────────────────────────────┐
│  完整的自动化回通知流程                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Copilot (1: 完成任务)     Claude (2: 检测交接)             │
│       │                      │                               │
│       ├─ 写交接文件            ├─ 读取结果                    │
│       ├─ 更新 status.json      ├─ 开始处理                    │
│       │                      └─ 回通知 ✅                     │
│       └─ 开始轮询                    │                      │
│                                    ↓                      │
│  Copilot (3: 检测回通知)                                  │
│       │                      ├─ 写 claude_notification.json  │
│       ├─ 检测到 RECEIVED         ├─ 写 user_notification.json │
│       └─ 响应：                 └─ 更新 handoff_status.json    │
│                                    ├─ HANDOFF_COMPLETE        │
│                                    └─ CLAUDE_OWNS_TASK         │
│                                    ↓                      │
│  双方确认 ✅                                               │
│                                                             │
│  流程结束：Copilot 待命，Claude 继续工作                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Copilot 检测到回通知时的执行清单

```markdown
## Copilot 检测到 "RECEIVED_AND_PROCESSING" 时的操作

### 1. 确认收到 Claude 的回通知
- [ ] 读取 handoff_status.json
- [ ] 确认 status === "RECEIVED_AND_PROCESSING"
- [ ] 读取 acknowledged_by === "claude_code"

### 2. 发送响应给 Claude
- [ ] 更新 handoff_status.json 为 "HANDOFF_COMPLETE"
- [ ] 写入 timeline 信息
- [ ] 标记状态为 "CLAUDE_OWNS_TASK"

### 3. 发送通知给用户（可选）
- [ ] 创建 user_notification.json
- [ ] 标注 action_required = false
- [ ] 提供任务完成摘要

### 4. 更新任务历史
- [ ] 在 rules/copilot_tasks.md 记录交接完成
- [ ] 更新任务历史时间线

### 5. 进入待命状态
- [ ] 检查是否有新任务
- [ ] 无任务则保持待命
- [ ] 等待下一次任务分配
```

---

## 📂 相关文件

| 文件 | 用途 | 写入者 | 读取者 |
|------|------|--------|--------|
| `claude_notification.json` | Copilot → Claude 通知 | Copilot | Claude |
| `user_notification.json` | 用户通知 | Copilot | VSCode/用户 |
| `handoff_status.json` | 状态同步 | 双方 | 双方 |
| `rules/copilot_tasks.md` | 任务历史 | Copilot | 双方 |

---

**触发检测频率**: 每 10 秒轮询一次 `handoff_status.json`
