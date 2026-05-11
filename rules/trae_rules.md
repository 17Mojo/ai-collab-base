# Trae AI 记忆系统规则

## 激活方式
当用户输入 `2X` 时，Trae AI 必须自动启动：
启动时必须立即响应：
Trae AI ACK: 记忆已激活，已读取 {规则文件列表}，准备执行。

## 执行规则

### 1. 读取规范
- 项目启动时加载 `rules/trae_rules.md`
- 加载 `rules/AI-COLLABORATION-STANDARDS.md`
- 加载 `rules/dev-record-template.md`

### 2. 执行流程
每次任务必须遵循以下流程：

```
Preflight → Plan → Implement → Validate → Record → Report
```

- **Preflight**: 检查冲突状态、读取相关记录
- **Plan**: 输出执行计划，标记风险点
- **Implement**: 执行开发，每30分钟记录一次状态
- **Validate**: 验证实现，记录验证结果
- **Record**: 写入开发日志到 `logs/trae-ai/YYYY-MM-DD_<task>.md`
- **Report**: 向用户汇报完成状态

### 3. 日志要求
- 每次任务必须写入 `logs/trae-ai/YYYY-MM/YYYY-MM-DD_<task>.md`
- 日志格式必须符合 `dev-record-template.md` 规范
- 包含：任务描述、执行步骤、变更文件、验证结果、时间戳

### 4. 冲突检测
- 修改文件前必须检查 `logs/collaboration_state.json`
- 如果目标文件被标记为 `implementing` 或 `testing`，必须暂停并通知用户
- 禁止同时修改同一文件的冲突操作

### 5. 定时机制
- 每2小时自动追加记录到当前日志
- 记录内容：当前状态、已完成工作、下一步计划

## 禁止行为
- ❌ 不读取规则直接开始开发
- ❌ 不检查冲突状态直接修改文件
- ❌ 不记录开发日志
- ❌ 同时处理多个未关联的任务
- ❌ 修改标记为 `conflict` 的文件

## 质量门控
- 所有代码必须通过类型检查
- 所有变更必须有验证覆盖
- 所有日志必须包含时间戳
- 所有冲突必须显式解决
