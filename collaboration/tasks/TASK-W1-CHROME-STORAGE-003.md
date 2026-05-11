# 任务: 本地存储版本迁移与清理

**任务ID**: TASK-W1-CHROME-STORAGE-003
**分配给**: copilot
**优先级**: P1
**创建时间**: 2026-02-28T14:52:12+08:00
**截止时间**: 2026-03-06T18:00:00+08:00

## 任务描述
引入 storage schema version、迁移策略和历史数据清理。

## 输入
- 文件:
  - products/prompt-pack-extension/chrome/src/background/index.js
  - products/prompt-pack-extension/chrome/src/options/options.js
  - docs/CHROME_EXTENSION_GUIDE.md
- 上下文: 按 4 周开发计划推进，避免跨周范围扩散
- 依赖: 无硬依赖，支持并行推进

## 输出要求
- 输出: 存储迁移机制 + 迁移说明
- 格式: 提交代码 + 测试结果 + 变更说明
- 结果文件: collaboration/results/RESULT_TASK-W1-CHROME-STORAGE-003.md

## 验证标准
- [ ] 旧版本数据可迁移且不丢关键配置
- [ ] 历史数据有上限与清理策略
- [ ] 迁移路径有测试覆盖

## 状态
- [ ] 待开始 (pending)
- [ ] 进行中 (in_progress)
- [ ] 已完成 (completed)
- [x] 已阻塞 (blocked)

## 备注
- 工单已自动发布，可立即领取执行。
- 2026-02-28: Copilot 暂时不可用，已转派到 `TASK-W1-CHROME-STORAGE-003-R1` (codex)。
