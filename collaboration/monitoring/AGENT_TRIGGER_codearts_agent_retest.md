# Agent Session Dispatch Payload（自动生成）

- Trigger: `WEEK 1-3 RETEST`
- Assignee: `codearts_agent` (CodeArts)
- GeneratedAt: `2026-04-07T10:00:00.000000`
- SourceOrders: `collaboration/monitoring/AGENT_DISPATCH_ORDERS_retest_w1_w3.md`

## 新鲜度校验（必须执行）

在执行任务前，必须先校验本 payload 的新鲜度：

```bash
# 1. 检查本 payload 的 GeneratedAt
# GeneratedAt: 2026-04-07T10:00:00.000000

# 2. 当前时间对比
# 如果时间差 > 5 分钟，则 payload 已过期

# 3. 如果 payload 已过期，执行一键修复：
python3 -m ai_collab.cli trigger --phrase 'WEEK 1-3 RETEST CodeArts' --target codearts_agent
```

**判定规则**：
- ✅ 新鲜：时间差 ≤ 5 分钟
- ⚠️  过期：时间差 > 5 分钟

**过期处理**：
1. 立即停止执行
2. 执行一键修复命令重新生成 payload
3. 使用新生成的 payload 继续执行

请将本文件完整发送到对应 Agent 会话，避免手工抽段造成漏项。

## 会话执行约束（必须遵守）

- 收到 `A.RUN` 后必须先读取本文件，再执行任务块。
- 系统级 RUN 只允许执行：`python3 -m ai_collab.cli run`（内置工作区门禁）。
- 禁止改为执行全局串联命令：`python3 -m ai_collab.cli dispatch && python3 -m ai_collab.cli receipt && python3 -m ai_collab.cli benefit`。
- 完成后仅回复一行 ACK；优先使用任务块中的 `python3 -m ai_collab.cli ack ...` 生成并原样回复：`A.ACK|task=<ids>|status=<ok/blocked/noop>|result=<paths>`。

## 发送给 `CodeArts` (`codearts_agent`)

### TASK-W1-W3-RETEST-001

```text
【执行指令 | TASK-W1-W3-RETEST-001】

任务: Week 1、2、3 综合复测与验收

1) 切换状态为 implementing
python3 -m ai_collab.cli tasks update --task-id TASK-W1-W3-RETEST-001 --ai codearts_agent --status implementing --note "Week 1-3 comprehensive retest"

2) 执行完整测试套件并记录所有输出
# Week 1 单元测试
pytest tests/unit/context/ tests/unit/pack/ -v --tb=short 2>&1 | tee /tmp/week1_unit_test.log

# Week 2 单元测试
pytest tests/unit/cli/ -v --tb=short 2>&1 | tee /tmp/week2_unit_test.log

# Week 3 单元测试
pytest tests/unit/pack/test_bulk.py tests/unit/pack/test_import.py tests/unit/pack/test_version.py tests/unit/pack/test_template.py tests/unit/pack/test_rating.py tests/unit/context/test_aggregator.py tests/unit/context/test_search.py -v --tb=short 2>&1 | tee /tmp/week3_unit_test.log

# 集成测试
pytest tests/integration/ -v --tb=short --cov=src.ai_collab --cov-report=term 2>&1 | tee /tmp/integration_test.log

3) 汇总测试结果（生成统计表格）
collaboration/results/RESULTS_W1_W3_RETEST_2026-04-07.md

4) 切换状态为 testing 并回报进展
python3 -m ai_collab.cli tasks update --task-id TASK-W1-W3-RETEST-001 --ai codearts_agent --status testing --note "comprehensive test results ready"

5) 生成 ACK 协议行（工具输出，原样回复）
python3 -m ai_collab.cli ack --task-id TASK-W1-W3-RETEST-001 --ai codearts_agent --status ok
```

## 复测范围说明

### Week 1: Context 基础基础设施
- Context Schema (schema.py)
- Context Recommender (recommender.py)
- Context Learner (learning.py)
- Context Enhancer (enhanced.py)

### Week 2: Pack 市场 CLI
- Pack Rating CLI (cli/pack_rating.py)
- Pack Version CLI (cli/pack_version.py)
- Pack Template CLI (cli/pack_template.py)
- 集成测试框架

### Week 3: Pack 批量操作 + 上下文搜索
- Pack Bulk Operations (pack/bulk.py)
- Pack Import/Export (pack/importer.py)
- Multi-Source Aggregation (integrations/multi_source.py)
- Context Aggregator (context/aggregator.py)
- Context Search Engine (context/search.py)
- CLI 命令集 (4 个)

## 验收标准

- 单元测试通过率 ≥ 95%
- 集成测试通过率 = 100%
- 代码覆盖率 ≥ 75%
- 测试统计表格完整
- 风险评估完成
