# 任务: 扩展消息通道可靠性提升

**任务ID**: TASK-W1-CHROME-MESSAGE-002
**分配给**: codex
**优先级**: P1
**创建时间**: 2026-02-28T14:52:12+08:00
**截止时间**: 2026-03-06T18:00:00+08:00

## 任务描述
统一 popup/background/content 消息协议，补充超时与错误码。

## 输入
- 文件:
  - products/prompt-pack-extension/chrome/src/background/index.js
  - products/prompt-pack-extension/chrome/src/content/message-handler.js
  - products/prompt-pack-extension/chrome/src/popup/popup.js
  - docs/CHROME_EXTENSION_GUIDE.md
- 上下文: 按 4 周开发计划推进，避免跨周范围扩散
- 依赖: 无硬依赖，支持并行推进

## 输出要求
- 输出: 统一消息协议文档 + 可靠性补丁
- 格式: 提交代码 + 测试结果 + 变更说明
- 结果文件: collaboration/results/RESULT_TASK-W1-CHROME-MESSAGE-002.md

## 验证标准
- [ ] 消息 action 与返回结构统一
- [ ] 超时和异常场景返回可诊断错误
- [ ] 手工 smoke 和自动测试通过

## 状态
- [ ] 待开始 (pending)
- [ ] 进行中 (in_progress)
- [x] 已完成 (completed)
- [ ] 已阻塞 (blocked)

## 备注
- 工单已自动发布，可立即领取执行。
- 2026-02-28: Codex 已接单并生成执行批次（.cc-claude-codex/codex-progress.md）。
- 2026-02-28: 已完成消息协议统一、超时封装、错误码标准化，并完成回归测试。
