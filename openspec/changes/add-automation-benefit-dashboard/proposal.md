# 增加自动化收益看板（Automation Benefit Dashboard）

## Why

S9 已具备自动派单（dispatch）与自动回执（receipt）能力，并完成单轮收益验证，但缺少“按天持续追踪 >3 目标”的统一看板，导致：
- 收益判定依赖临时人工计算
- 无法持续观察趋势与稳定性
- 难以形成 Go/No-Go 的日常量化证据

需要新增自动化收益看板能力，对控制面效率进行日维度自动统计与展示。

## What Changes

- 新增收益看板脚本：
  - 读取 dispatch/receipt history
  - 按天聚合任务处理量与自动化触点
  - 计算效率比与达标情况（默认目标 >3）
  - 输出 Markdown 看板与 JSON 报告
- 在 CLI 新增 `benefit` 命令，统一触发脚本并支持配置覆盖。
- 在初始化配置中增加 `benefit` 默认配置段。
- 补齐单元测试（脚本行为 + CLI 命令/路由）。

## Impact

- Affected specs: `task-governance`
- Affected code:
  - `collaboration/scripts/build_automation_benefit_dashboard.py`
  - `ai_collab/cli.py`
  - `tests/unit/test_automation_benefit_dashboard.py`
  - `tests/unit/test_cli.py`
  - `.vscode/ai-collab.json`
- 风险控制：
  - 看板只做统计与输出，不直接改任务状态
  - 对缺失/损坏历史文件采用容错处理（无数据时输出空看板）
