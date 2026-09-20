---
task_id: TASK-P0-CONSENSUS-ENGINE-001
change_id: migrate-parallel-architecture-to-hermes
status: ready_to_implement
priority: P0
assignee: codearts_agent
reviewer: user
status_updated_at: 2026-09-20T12:25:00+08:00
primary_skill: backend-architect
support_skills:
  - asyncio-programming
  - testing
  - documentation
created_at: 2026-06-01T13:50:00Z
acceptance_commands:
  - "pytest tests/unit/hermes/test_consensus_engine.py -v --cov=hermes.engines.consensus_engine"
  - "python3 -c \"from hermes.engines.consensus_engine import ConsensusEngine; print('OK')\""
result_file: collaboration/results/RESULT-P0-CONSENSUS-ENGINE-001.md
---

# 任务：移植 consensus_engine 到 Hermes

## 背景

从 ai-collab-base 移植 `consensus_engine.py` 到 Hermes，实现多模型并发查询能力，预期将报告生成延迟降低 60%。

## 目标

将 ai-collab-base 的 `ai_collab/engines/consensus_engine.py` 移植到 Hermes，实现：
1. 多模型并发查询（asyncio.gather）
2. 超时控制（全局 + 单 provider）
3. 重试机制（max_retries=3）
4. 结果归一化

## 步骤

### Step 1: 创建目标目录结构

**命令**:
```bash
ssh openclaw "mkdir -p ~/.hermes/hermes-agent/engines"
```

**验证**: 目录存在

### Step 2: 移植代码

**源文件**: `/Users/raymondna/Documents/AI-collab/ai-collab-base/ai_collab/engines/consensus_engine.py`

**目标**: `~/.hermes/hermes-agent/engines/consensus_engine.py`

**改造点**:
1. `providers` → `models` (适配 Hermes 配置)
2. 添加 Hermes 日志集成 (`from hermes.logger import log`)
3. 移除 ai-collab 特有依赖

**命令**:
```bash
# 本地改造后上传
scp consensus_engine_hermes.py openclaw:~/.hermes/hermes-agent/engines/consensus_engine.py
```

### Step 3: 创建 __init__.py

**文件**: `~/.hermes/hermes-agent/engines/__init__.py`

**内容**:
```python
from .consensus_engine import ConsensusEngine

__all__ = ["ConsensusEngine"]
```

### Step 4: 修改 config.yaml

**文件**: `~/.hermes/config.yaml`

**新增配置段**:
```yaml
engines:
  consensus:
    enabled: true
    max_concurrent: 5
    global_timeout: 60
    retry:
      max_retries: 3
      backoff: exponential
    fallback_mode: partial  # 部分失败仍返回成功结果
```

### Step 5: 修改 ai-media-analysis-report.py

**文件**: `~/.openclaw-mac/workspace/ai-media-analysis-report.py`

**改造点**:
1. 导入 ConsensusEngine
2. 替换 `_llm_investor_insight()` 串行调用为并行

**示例**:
```python
from hermes.engines import ConsensusEngine

async def generate_parallel_insights(topics):
    engine = ConsensusEngine(config_path="~/.hermes/config.yaml")
    results = await engine.query_multiple_models(topics)
    return {topic: r["content"] for topic, r in zip(topics, results)}
```

### Step 6: 编写单元测试

**文件**: `~/.hermes/hermes-agent/tests/unit/test_consensus_engine.py`

**测试用例**:
```python
import pytest
from hermes.engines import ConsensusEngine

@pytest.mark.asyncio
async def test_concurrent_query():
    engine = ConsensusEngine()
    results = await engine.query_multiple_models(["tech", "market"])
    assert len(results) == 2
    assert all(r["status"] == "success" for r in results)

@pytest.mark.asyncio
async def test_timeout_isolation():
    engine = ConsensusEngine(global_timeout=1)
    # 模拟超时 provider
    results = await engine.query_multiple_models(["timeout_topic"])
    # 应该返回空结果而非异常
    assert isinstance(results, list)
```

### Step 7: 执行验收命令

```bash
pytest tests/unit/hermes/test_consensus_engine.py -v --cov=hermes.engines.consensus_engine
```

**期望**: 所有测试通过，覆盖率 ≥ 80%

### Step 8: 性能基准测试

**文件**: `benchmarks/parallel_insight_generation.py`

**验证**: 并行延迟 < 串行延迟 / 并发数

## 验收标准

- [ ] `consensus_engine.py` 成功移植到 Hermes
- [ ] 单元测试全部通过
- [ ] 覆盖率 ≥ 80%
- [ ] config.yaml 包含 engines 配置段
- [ ] ai-media-analysis-report.py 使用 ConsensusEngine
- [ ] 性能基准：延迟降低 ≥ 50%

## 完成后回复

```
A.ACK|task=TASK-P0-CONSENSUS-ENGINE-001|status=ok|result=consensus_engine已移植，延迟降低XX%
```

## 参考文档

- 源代码: `/Users/raymondna/Documents/AI-collab/ai-collab-base/ai_collab/engines/consensus_engine.py`
- OpenSpec: `openspec/changes/migrate-parallel-architecture-to-hermes/`
- 路线图: `/Users/raymondna/Documents/NAS Docker/ROADMAP.md`

## 状态更新 (2026-09-20T12:25:00+08:00)

### ✅ 本地准备完成
- [x] Hermes 移植版本已准备: 
- [x] config.yaml 已配置 (max_concurrent=5, global_timeout=60, max_retries=3)
- [x] 单元测试已编写: 
- [x] __init__.py 已创建
- [x] RESULT 文件已生成: 

### ⏸️ 待远程执行 (需 openclaw SSH)
- [ ] 上传  到 openclaw:~/.hermes/hermes-agent/engines/
- [ ] 修改 ~/.hermes/config.yaml
- [ ] 修改 ai-media-analysis-report.py
- [ ] 运行验收命令

### 📊 当前进度
- 本地准备: 100% 完成
- 远程执行: 0% (待 Hermes 环境访问)
- 任务状态: pending → ready_to_implement
