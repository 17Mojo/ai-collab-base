# 任务: VSCode 命令面板扩展化

**任务ID**: TASK-W2-VSCODE-COMMANDS-002
**分配给**: codex
**优先级**: P1
**创建时间**: 2026-02-28T14:52:12+08:00
**截止时间**: 2026-03-13T18:00:00+08:00

## 任务描述
将现有 tasks 迁移为 VSCode 扩展命令（registerCommand）。

## 输入
- 文件:
  - products/vscode-extension/
  - .vscode/tasks.json
  - README.md
- 上下文: 按 4 周开发计划推进，避免跨周范围扩散
- 依赖: 无硬依赖，支持并行推进

## 输出要求
- 输出: 命令面板可直接调用核心流程
- 格式: 提交代码 + 测试结果 + 变更说明
- 结果文件: collaboration/results/RESULT_TASK-W2-VSCODE-COMMANDS-002.md

## 验证标准
- [ ] 至少 5 个核心命令支持命令面板触发
- [ ] 命令参数与当前 CLI 兼容
- [ ] README 提供使用示例

## 状态
- [x] 待开始 (pending)
- [ ] 进行中 (in_progress)
- [ ] 已完成 (completed)
- [ ] 已阻塞 (blocked)

## 备注
- 工单已自动发布，可立即领取执行。