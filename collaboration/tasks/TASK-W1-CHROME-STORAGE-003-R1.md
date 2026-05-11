# 任务: 本地存储版本迁移与清理（替代执行）

**任务ID**: TASK-W1-CHROME-STORAGE-003-R1
**分配给**: codex
**优先级**: P1
**创建时间**: 2026-02-28T14:56:06+08:00
**截止时间**: 2026-03-06T18:00:00+08:00

## 任务描述
[replacement] 引入 storage schema version、迁移策略和历史数据清理，修复 Options 设置入口与 Background 存储规范不一致的问题。

## 输入
- 文件:
  - products/prompt-pack-extension/chrome/src/background/index.js
  - products/prompt-pack-extension/chrome/src/options/options.js
  - docs/CHROME_EXTENSION_GUIDE.md
  - tests/e2e/test_integration.py
- 上下文: 替代工单，原工单 `TASK-W1-CHROME-STORAGE-003` 因 Copilot 暂不可用而转派

## 输出要求
- 输出: schema 迁移补丁 + 设置入口统一 + 验证用例
- 格式: 提交代码 + 测试结果 + 变更说明
- 结果文件: collaboration/results/RESULT_TASK-W1-CHROME-STORAGE-003-R1.md

## 验证标准
- [x] 存储 schema 版本化与迁移逻辑可用
- [x] Options 页面通过 Background 接口读写设置
- [x] 历史清理与设置归一化逻辑可验证
- [x] 自动化测试通过

## 状态
- [ ] 待开始 (pending)
- [ ] 进行中 (in_progress)
- [x] 已完成 (completed)
- [ ] 已阻塞 (blocked)

## 备注
- 2026-02-28: Codex 接管 Copilot 替代工单并完成收口。
