# Agent Dispatch Orders（自动生成）

- 生成时间: `2026-04-07T10:00:00`
- 待派发任务数: `1`

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

### Week 1: Context 基础设施
- 上下文模式
- 推荐引擎
- 学习模块
- 增强功能

### Week 2: Pack 市场 CLI
- Pack 评分
- Pack 版本管理
- Pack 模板
- 集成测试

### Week 3: Pack 批量操作 + 上下文搜索
- Pack 批量操作
- Pack 导入导出
- 多源知识聚合
- 智能上下文搜索
- 集成测试

## 验收标准

- 单元测试通过率 ≥ 95%
- 集成测试通过率 = 100%
- 代码覆盖率 ≥ 75%
