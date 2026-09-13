# Change Proposal: Migrate Parallel Architecture to Hermes

## Why

当前 OpenClaw × Hermes 协同架构存在效率瓶颈：
1. 报告生成单次同步调用，无并行能力
2. 无任务队列和状态管理，失败需全量重跑
3. 多 Agent 协同未实现，吞吐量受限

ai-collab-base 项目已实现成熟的并行架构（consensus_engine/state_manager/notification），可直接移植到 Hermes。

**预期效果**：
- 单 Agent 并行：延迟 -60%
- 长任务管理：可靠性 +50%
- 多 Agent 并行：吞吐量 +300%

## What Changes

### 移植模块清单

| 源模块 | 目标位置 | 核心能力 | 优先级 |
|--------|---------|---------|--------|
| `consensus_engine.py` | Hermes `engines/` | asyncio 并发查询 + 超时控制 + 结果归一化 | P0 |
| `state_manager.py` | Hermes `core/` | 任务状态机 + checkpoint + 冲突检测 | P1 |
| `notification.py` | Hermes `messaging/` | broadcast/@mention/direct 三种通知模式 | P1 |
| `intervention_queue.py` | Hermes `queue/` | 人工干预队列 + 摘要生成 | P2 |
| `dispatch_trigger.py` | OpenClaw `scheduler/` | 任务派发 + Payload 生成 | P2 |

### 影响范围

- **新增文件**: `~/.hermes/hermes-agent/engines/consensus_engine.py` 等
- **修改文件**: `~/.hermes/config.yaml` (新增 engines 配置)
- **新增依赖**: `asyncio` (标准库), `aiohttp` (HTTP 并发)
- **影响系统**: Hermes Agent, OpenClaw scheduler, ai-media-analysis-report.py

### 风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| asyncio 与现有同步代码冲突 | 中 | 逐步迁移，新旧并存 |
| 状态文件并发写入冲突 | 中 | 移植文件锁机制 |
| Hermes 内存占用增加 | 低 | 配置并发上限 (max_concurrent=5) |
| 向后兼容性破坏 | 低 | 保留旧接口，新增并行入口 |

## Impact

- **Affected specs**: `hermes-parallel-architecture` (新增)
- **Affected code**:
  - `~/.hermes/hermes-agent/engines/consensus_engine.py`
  - `~/.hermes/hermes-agent/core/state_manager.py`
  - `~/.hermes/hermes-agent/messaging/notification.py`
  - `~/.openclaw-mac/workspace/scripts/smart-report-scheduler.sh`
  - `~/.openclaw-mac/workspace/ai-media-analysis-report.py`
- **ROI**: P0 任务 3 天见效，延迟 -60%
