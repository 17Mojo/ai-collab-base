# Codex `spawn_agent` 使用准则

**版本**: 1.0.0  
**生效日期**: 2026-03-17  
**适用范围**: Codex 技术合伙人会话内的内部子代理委派

---

## 1. 目标

本准则将 Codex 的 `spawn_agent` 能力纳入本项目协作治理体系，目标是：

1. 最大化利用 Codex 会话内可并行资源
2. 缩短分析、实现、验证的总耗时
3. 避免与 Claude / CodeArts 正式工单体系发生职责冲突
4. 避免内部并行演变为文件写冲突、状态漂移或审计失真

---

## 2. 定义

### 2.1 什么是 `spawn_agent`

`spawn_agent` 是 Codex 在**单个父任务**内临时拉起的内部子代理能力，用于：

- 并行代码探索
- 并行局部实现
- 并行测试与验证
- 并行整理审查材料

### 2.2 什么不是 `spawn_agent`

以下内容**不属于** `spawn_agent` 范畴：

- Claude Code / CodeArts Agent 的正式派单
- `TASK-*` 工单的外部执行
- `ACK|task=` 协议回复
- `collaboration_state.json` 中新增独立外部任务
- 用户产品决策、架构裁决、合并裁决

结论：
`spawn_agent` 是 **Codex 的内部执行工具**，不是新的正式协作角色。

---

## 3. 与现有协作体系的关系

### 3.1 与 Claude / CodeArts 的边界

`spawn_agent` 不替代现有多 AI 派单体系。

| 能力 | 默认归属 |
|---|---|
| 正式工单派发、`TASK-*` 跟踪、`ACK|task=` 回执 | Claude / CodeArts / Codex 主线程 |
| 会话内并行探索、局部实现、验证 | Codex `spawn_agent` |
| 技术路线、风险裁决、merge 决策 | Codex 主线程 |

### 3.2 审计口径

- 子代理产出默认视为 **Codex 主线程的内部工作结果**
- 子代理不能单独充当 `owner`、不能单独生成正式 `ACK`
- 最终对外结论、正式结果文档、合并动作必须由 Codex 主线程落账

---

## 4. 允许使用的场景

满足“目标明确 + 写集清晰 + 能明显提速”时，允许使用 `spawn_agent`。

### 4.1 优先场景

1. 并行只读探索
   - 例如同时检查 `cli.py`、`dispatch_trigger.py`、`state_manager.py` 的调用链

2. 并行验证
   - 例如一个子代理跑定向 pytest，另一个核查 CI/workflow，主线程继续修主线

3. 并行小范围实现
   - 例如一个子代理只负责独立测试文件，另一个只负责独立脚本

4. 并行审查辅助
   - 例如一个子代理核对 PR 范围污染，另一个核对提交依赖链

5. 并行文档整理
   - 例如一个子代理生成 PR 摘要，主线程继续做代码验证

### 4.2 推荐优先级

1. 只读探索
2. 定向验证
3. 不重叠写集的小实现
4. 文档/汇总整理

---

## 5. 禁止使用的场景

以下场景禁止使用 `spawn_agent`，必须由 Codex 主线程单独处理：

1. 主路径架构决策
2. merge / rebase / cherry-pick / force-push 决策
3. 正式派单策略、`TASK-*` 编排和优先级裁决
4. `ACK|task=` 协议输出与正式结果落账
5. 修改同一文件或同一模块的重叠写入
6. 需要立即依赖结果才能继续下一步的阻塞性任务
7. 涉及锁板、owner lock、state drift、receipt/dispatch 状态裁决的最终动作

特别禁止：

- 两个子代理同时写同一文件
- 子代理自行回滚他人修改
- 子代理擅自改动 `collaboration/monitoring/AGENT_TRIGGER_*`
- 子代理直接生成或发送正式 ACK

---

## 6. 写集隔离规则

### 6.1 强制原则

每次委派都必须明确写集边界。

允许：

- 子代理 A 只改测试文件
- 子代理 B 只改文档文件
- 主线程改主实现文件

禁止：

- 主线程和子代理同时改同一个文件
- 两个子代理改同一目录下同一逻辑面的重叠文件集

### 6.2 标准写法

委派任务时必须明确说明：

1. 负责文件
2. 不可改文件
3. 是否允许直接提交代码
4. 最终需要返回什么产物

示例要求：

```text
你负责 tests/unit/test_xxx.py。
不要修改 ai_collab/cli.py。
你不是唯一在代码库里工作的代理，不要回滚他人的修改。
完成后返回你改过的文件路径和验证结果。
```

推荐补充元数据，降低自动 preflight 误判：

```text
Parent Task: TASK-XXX
Files: tests/unit/test_xxx.py
Read Only: false
```

---

## 7. 执行流程

### 7.1 启动前判断

Codex 主线程在拉起子代理前，必须先判断：

- 当前任务是否能拆成并行子问题
- 子问题是否存在明确边界
- 子代理结果是否不会阻塞主线程立刻前进
- 是否比本地串行处理更省时

若以上任一项不成立，则不应委派。

进入写入型或正式任务上下文下的委派前，先运行运行时守卫：

```bash
python3 -m ai_collab.cli spawn-agent-guard --actor codex --parent-task <TASK-ID> --files <path1> <path2>
python3 -m ai_collab.cli spawn-agent-guard --actor codex --parent-task <TASK-ID> --read-only
```

若门禁返回阻断，先修正 parent task、写集或保护路径问题，再使用 `spawn_agent`。

安装 `python3 -m ai_collab.cli codex hooks --action install` 后，同一 guard 会在 Claude Code 实际执行 `Agent` 委派前自动运行；上面的 CLI 入口保留用于手动诊断和预演。

### 7.2 标准流程

1. 主线程先确定主路径
2. 将非阻塞侧任务拆给子代理
3. 主线程继续推进本地关键路径
4. 子代理返回后，由主线程统一复核并集成
5. 正式对外更新仍由主线程执行

### 7.3 等待策略

- 不要频繁 `wait_agent`
- 只有在主路径被结果阻塞时才等待
- 子代理运行期间，主线程必须继续做非重叠工作

---

## 8. 与正式工单体系的衔接规则

### 8.1 正式工单优先

如果任务已经进入正式协作体系：

- `collaboration/tasks/TASK-*.md`
- `collaboration/results/RESULT_*.md`
- `A.RUN / C.RUN / X.RUN`
- `ACK|task=...`

则 `spawn_agent` 只能作为 Codex 的**内部辅助手段**，不能绕过现有协议。

### 8.2 正式落账责任

以下动作必须由 Codex 主线程完成：

1. 派单
2. 状态更新
3. ACK 口径确认
4. PR review 结论
5. merge / rollback / 接管决策

---

## 9. 资源最大化策略

### 9.1 默认策略

当满足委派条件时，Codex 应优先考虑：

1. 主线程处理关键路径
2. 子代理并行处理侧向验证/探索
3. Claude / CodeArts 继续处理正式外部工单

这是“外部工单并行 + 会话内子代理并行”的双层资源利用方式。

### 9.2 典型高收益用法

1. CI / gate / lint 失败根因并行排查
2. Playwright 子套件并行验证
3. ACK / dispatch / monitoring 调用链并行核查
4. PR 范围污染核查
5. 文档与结果摘要整理

---

## 10. 失败与回退规则

若出现以下情况，立即停止继续扩散子代理使用：

1. 子代理写集与主线程发生冲突
2. 子代理结果与主线程判断持续不一致
3. 子代理导致状态文件、监控文件、正式工单文档被误改
4. 子代理等待成本高于串行处理收益

处理方式：

1. 停止新的子代理委派
2. 由主线程接管最终判断
3. 必要时丢弃子代理结果，不直接合并

---

## 11. 项目级硬规则

1. `spawn_agent` 只允许作为 **Codex 单任务内委派**
2. `spawn_agent` 不得替代 Claude / CodeArts 正式工单体系
3. 子代理不得直接产出正式 `ACK|task=`
4. 子代理不得在未声明写集的情况下修改文件
5. 主线程必须保留最终技术与治理裁决权

---

## 12. 参考关系

本准则由以下文件共同约束：

- `rules/codex_agent_rules.md`
- `collaboration/PROTOCOL.md`
- `rules/AI-COLLABORATION-STANDARDS.md`
- `collaboration/CROSS_AI_COLLABORATION_STANDARDS.md`

如出现冲突，以“单任务内委派、不得绕过正式工单体系、不得突破写集隔离”三条为最高解释原则。
