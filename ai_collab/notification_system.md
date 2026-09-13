# @Mention 通知系统设计

> **类比**: 微信群聊的三种提醒模式
> **目标**: Claude / Copilot / 你 之间自动化信息共享

---

## 🎯 三种通知模式

### 模式 1: 广播（发消息到群里）

```
用法：消息发布给所有人，默认所有人可见
对应：群公告、状态更新
```

### 模式 2: 广播 + @提醒人（重点提醒）

```
用法：发到群里 + @某个人，确保TA一定会看到
对应：@"某某 看一下这个问题"、紧急任务分配
```

### 模式 3: @提醒人 不广播（直接沟通）

```
用法：只有被@的人能看到
对应：私密交接、敏感信息传递
```

---

## 📐 通知消息格式

### 通用消息格式

```json
{
  "message_id": "MSG-20260226-001",
  "timestamp": "2026-02-26T15:00:00.000Z",
  "sender": "claude_code",
  "mode": "broadcast",  // broadcast | broadcast@mention | direct
  "content": "消息内容",
  "priority": "normal",    // low | normal | high | urgent

  // 模式 1: 广播 - 所有人可见
  "recipients": ["claude_code", "copilot", "user"],
  "broadcast": true,

  // 模式 2: 广播 + @提醒
  "broadcast": true,
  "@_mentions": ["copilot"],  // 强制提醒这些人

  // 模式 3: 直接沟通 - 只有被@的人可见
  "broadcast": false,
  "@_direct_target": "claude_code",

  // 元数据
  "metadata": {
    "related_files": [],
    "action_required": false,
    "deadline": null,
    "context": {...}
  }
}
```

---

## 🔄 自动化通知流程

```
┌─────────────────────────────────────────────────────────────┐
│                    通知系统流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  发送者触发通知                                        │   │
│  │                                                          │   │
│  │  // 模式1: 广播                                        │   │
│  │  emit("broadcast", "系统状态更新：完成度85%")          │   │
│  │                                                          │   │
│  │  // 模式2: 广播 + @                                      │   │
│  │  emit("@copilot 处理研究结果")                         │   │
│  │                                                          │   │
│  │  // 模式3: 直接沟通                                    │   │
│  │  emit_direct("@copilot", "私密交接信息")              │   │   │
│  │                                                          │   │
│  └──────────┬──────────────────────────────────────┘   │
│             ↓                                              │   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  存储Notification()                                   │   │
│  │  ├─ 写入消息队列                                     │   │
│  │  ├─ 设置目标 recipients                               │   │
│  │  └─ 标记优先级                                      │   │
│  └──────────┬──────────────────────────────────────┘   │
│             ↓                                              │   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Distribute()                                          │   │
│  │  ├─ 检查目标 AI 是否活跃                              │   │
│  │  ├─ 如果不活跃，写入待通知列表                        │   │
│  │  └─ 如果活跃，立即分发                               │   │
│  └──────────┬──────────────────────────────────────┘   │
│             ↓                                              │   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  目标 AI 收到通知                                       │   │
│  │                                                          │   │
│  │  ├── 写入 {ai}_notification.json                      │   │
│  │  ├── 更新 unread 标记                                   │   │
│  │  └─ 触发检测循环启动                                  │   │
│  └──────────┬──────────────────────────────────────┘   │
│             ↓                                              │   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  读取后自动标记已读                                     │   │
│  │                                                          │   │
│  │  // AI 的检测循环（每 5 秒）                           │   │
│  │  while (true):                                          │   │
│  │     if (hasUnreadNotifications()):                     │   │
│  │       processAndMarkAsRead()                          │   │
│  │     sleep(5)                                           │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────┘   │
│             ↓                                              │   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  回执确认（可选）                                        │   │
│  │  └─ 标记已处理 @notification.read_at                │   │
│  │                                                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 💡 三种模式的使用场景

### 广播 - 系统状态共享

```python
# Claude 广播状态更新
def broadcast_status(progress: int):
    emit("broadcast", {
        "sender": "claude_code",
        "content": f"系统进度更新：{progress}%",
        "priority": "normal"
    })
    # → claude_notification.json (Copilot也能看到)
    # → copilot_notification.json
```

### 广播 + @提醒 - 紧急任务

```python
# 你在 VSCode 中紧急提醒 Copilot
def @mention_urgent_task():
    emit("@copilot", {
        "mode": "broadcast@mention",
        "content": "紧急：网络调研结果需要补充技术细节",
        "priority": "urgent",
        "@_mentions": ["copilot"]
    })
    # → 所有人看到，但 Copilot 被强烈标记
    # → copilot_notification.json 增加 "important": true
```

### 直接沟通 - 私密交接

```python
# Copilot 给 Claude 的私密信息
def direct_handoff():
    emit_direct("@claude", {
        "mode": "direct",
        "content": "私有 API key: xxx-xxx-xxx",
        "priority": "high",
        "@_direct_target": "claude_code"
    })
    # → 只有 claude_notification.json 被创建
    # → 其他人看不到
```

---

## 📁 文件系统设计

```
notifications/
├── message_queue.json              # 全局消息队列
├── claude_notification.json       # Claude 的通知
├── copilot_notification.json      # Copilot 的通知
├── user_notification.json         # 用户的通知
└── notification_history.json      # 历史记录
```

### message_queue.json 结构

```json
{
  "queue_id": "QUEUE-20260226",
  "messages": [
    {
      "id": "MSG-001",
      "mode": "broadcast",
      "sender": "claude_code",
      "content": "状态更新",
      "timestamp": "2026-02-26T15:00:00.000Z",
      "recipients": ["claude_code", "copilot"],
      "read_by": ["claude_code"]
    }
  ]
}
```

---

## 🔍 检测和确认机制

### AI 检测循环（自动执行）

```python
def notification_detection_loop():
    while True:
        # 1. 检查是否有新通知
        if has_new_notifications():
            # 2. 读取并处理
            for notification in read_pending_notifications():
                process_notification(notification)
                mark_as_read(notification.id)

            # 3. 回执确认
            send_acknowledgement()

        # 每 5 秒检查一次
        sleep(5)

def send_acknowledgement():
    """最后一个通知的处理确认"""
    last_notification = get_last_notification()

    # 回执谁处理的，什么时候完成的
    write_json("notification_ack.json", {
        "notification_id": last_notification.id,
        "processed_by": current_ai,
        "processed_at": datetime.now().isoformat(),
        "status": "COMPLETED"
    })
```

---

## 📝 API 示例

### 发送广播

```python
# 发送消息给所有人
broadcast("所有 Pack 代码已完成，开始测试阶段")
```

### 发送 @提醒

```python
# @提醒某人处理
@mention("copilot", "请检查并补充 OpenSpec 规范的实现细节")
```

### 发送私密信息

```python
# 直接沟通，只有对方能看到
direct("copilot", "私密交接信息：API配置在环境变量中")
```

---

## 🎯 自动化程度

| 场景 | 自动化程度 | 说明 |
|------|-----------|------|
| 常规通知更新 | ✅ 完全自动 | 发送→检测→确认 全自动 |
| 紧急任务 | ✅ 完全自动 | +push 通知 |
| 人员切换 | ✅ 完全自动 | @提醒 → 对方自动响应 |
| 网络任务分配 | ✅ 完全自动 | 写入任务队列 → 对方自动开始 |
| 确认同步 | ⏸️ 需手动确认 | 重大决策前需人工确认 |
