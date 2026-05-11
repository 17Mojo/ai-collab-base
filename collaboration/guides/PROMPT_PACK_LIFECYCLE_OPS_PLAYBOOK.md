# Prompt Pack 生命周期执行手册

## 1. 生命周期阶段

- Generation: 产出新能力草案
- Review: 质量、风险、边界审查
- Iteration: 基于反馈迭代
- Archive: 归档为可复用能力资产

## 2. OpenSpec 绑定规则

生命周期相关变更必须绑定 `change_id` 并通过严格校验：

```bash
openspec validate <change-id> --strict
```

## 3. 工单派发规则

生命周期执行工单最少包含：
- `change_id`
- `primary_skill` / `support_skills`
- `acceptance_commands`
- `result_file`

## 4. Stage 入口/出口准则

### Generation
- 入口：需求目标和边界明确
- 出口：proposal/tasks/spec delta 可审阅

### Review
- 入口：代码/文档改动可运行
- 出口：验收命令通过，风险可解释

### Iteration
- 入口：有明确偏差或反馈
- 出口：偏差项闭环，结果文档更新

### Archive
- 入口：变更为 Complete
- 出口：归档路径与回滚信息齐备

## 5. 证据模板

每个生命周期工单需在 `RESULT_TASK-*.md` 包含：
- 执行命令
- 通过/失败结论
- 偏差与纠偏
- 风险与回滚点

## 6. 管理口径

- Codex: 生命周期编排和门禁
- Claude: 主要实现执行
- CodeArts: 验证/测试/文档辅助
