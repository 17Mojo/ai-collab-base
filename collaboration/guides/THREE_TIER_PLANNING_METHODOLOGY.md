# 三级计划体系方法论

**创建日期**: 2026-06-01
**来源**: 移植并行架构到 Hermes 项目实践
**适用范围**: 所有需要 OpenSpec 管理的技术改造项目

---

## 一、三级层次定义

```
┌─────────────────────────────────────────────────────────┐
│  一级：战略层（OpenSpec）                                │
│  职责：定目标、定方向、定验收标准                         │
│  产物：proposal.md + spec.md                             │
│  特点：不涉及具体执行，只回答"为什么做""做什么"           │
└─────────────────────────────────────────────────────────┘
                          ↓ 分解
┌─────────────────────────────────────────────────────────┐
│  二级：战术层（任务分解）                                │
│  职责：根据一级分解为可执行任务，分配资源                 │
│  产物：TASK-*.md（绑定 change_id）                       │
│  特点：一个 OpenSpec 对应多个 TASK，明确执行者和验收命令   │
└─────────────────────────────────────────────────────────┘
                          ↓ 派发
┌─────────────────────────────────────────────────────────┐
│  三级：执行层（过程派单）                                │
│  职责：任务执行中的动态调整、状态跟踪、阻塞处理           │
│  产物：payload 文件 + 状态记录 + 调整日志                 │
│  特点：运行时调整，响应实际情况                           │
└─────────────────────────────────────────────────────────┘
```

---

## 二、每一级的职责边界

### 一级（OpenSpec）

**做什么**：
- 定义变更原因（Why）
- 定义变更内容（What）
- 定义影响范围（Impact）
- 定义需求变更（Spec Delta：ADDED/MODIFIED/REMOVED Requirements）

**不做什么**：
- ❌ 不指定具体执行者
- ❌ 不写具体实现步骤
- ❌ 不涉及时间安排

**验收标准**：
- ✅ `proposal.md` 包含 Why/What/Impact 三部分
- ✅ `spec.md` 使用 SHALL/MUST（非 should/may）
- ✅ 每个 Requirement 至少有 1 个 Scenario
- ✅ Scenario 格式：`#### Scenario: ...`（四个 hashtag）

**命令**：
```bash
openspec validate <change_id> --strict
```

---

### 二级（任务分解）

**做什么**：
- 根据 OpenSpec 分解为多个 TASK
- 每个 TASK 绑定 `change_id`（指向一级）
- 分配 `assignee` 和 `reviewer`
- 定义 `acceptance_commands`（具体验证命令）
- 定义 `result_file`（结果文件路径）

**不做什么**：
- ❌ 不重复一级的 Why/What（只引用）
- ❌ 不在执行中动态调整（那是三级）
- ❌ 不创建 payload 文件（那是三级）

**验收标准**：
- ✅ 每个 TASK 的 `change_id` 指向存在的 OpenSpec
- ✅ 每个 TASK 有明确的 `assignee`
- ✅ 每个 TASK 有可执行的 `acceptance_commands`
- ✅ TASK 的验收标准与一级 Spec Delta 对应

**命令**：
```bash
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
```

---

### 三级（过程派单）

**做什么**：
- 创建 payload 文件（派单指令）
- 记录任务状态变更
- 处理阻塞和依赖
- 动态调整执行者/优先级
- 生成干预队列

**不做什么**：
- ❌ 不修改一级 OpenSpec（除非回溯变更）
- ❌ 不修改二级 TASK 的核心内容（只调整执行细节）
- ❌ 不跳过验收直接完成

**产物位置**：
```
collaboration/monitoring/payload_<agent>_latest.json
collaboration/dispatch/payloads/TASK-*.json
logs/collaboration_state.json
collaboration/interventions/*.json
```

**调整场景**：
| 场景 | 动作 | 记录位置 |
|------|------|---------|
| 执行者变更 | 修改 assignee，生成新 payload | `collaboration_state.json` |
| 优先级调整 | 修改 priority，重新排序派发 | payload 文件 |
| 阻塞处理 | 标记 blocked，记录 blocker_task_id | `intervention_queue.py` |
| 验收调整 | 修改 acceptance_criteria，补充命令 | TASK 文件 + payload |

---

## 三、常见错误（本次踩坑）

### 错误 1：一级写了二级内容

**表现**：在 `proposal.md` 里写了具体任务分解和时间线

**后果**：
- 一级不再纯粹，难以复用
- 二级重复内容，维护成本增加
- 一级变更时，需要同步修改多处

**正确做法**：
- 一级只写 Why/What/Impact
- 任务分解放到 `tasks.md`（辅助文件，非核心产物）
- 二级 TASK 引用一级，不重复内容

---

### 错误 2：立即创建三级 payload

**表现**：在二级 TASK 还未确认时，就创建了 payload 文件

**后果**：
- 如果二级调整，payload 需要重新生成
- 派单过早，可能派给错误的执行者
- 浪费调整成本

**正确做法**：
- 等二级 TASK 确认（assignee、acceptance_commands 确定）
- 再创建三级 payload 派单
- 流程：一级确认 → 二级分解 → 二级确认 → 三级派单

---

### 错误 3：三级跳过二级直接修改

**表现**：执行中发现问题，直接修改 TASK 文件，未记录调整原因

**后果**：
- 失去过程留痕
- 无法追溯决策原因
- 后续类似问题难以复用经验

**正确做法**：
- 三级调整需记录到 `intervention_queue` 或状态日志
- 重大调整需更新二级 TASK（并记录变更原因）
- 所有关键变更都留痕

---

## 四、正确工作流

### 阶段 1：一级规划（战略）

```bash
# 1. 创建 OpenSpec Change
mkdir -p openspec/changes/<change_id>/specs/<spec_name>

# 2. 编写 proposal.md（Why/What/Impact）
cat > openspec/changes/<change_id>/proposal.md << 'EOF'
## Why
[为什么需要这个变更]

## What Changes
[具体变更内容]

## Impact
[影响范围和风险]
EOF

# 3. 编写 spec.md（Spec Delta）
cat > openspec/changes/<change_id>/specs/<spec_name>/spec.md << 'EOF'
## ADDED Requirements
### Requirement: ...
#### Scenario: ...
EOF

# 4. 验证
openspec validate <change_id> --strict

# 5. 等待审批
# （人工确认是否继续）
```

**输出**：
- `proposal.md`
- `spec.md`
- 验证通过报告

---

### 阶段 2：二级分解（战术）

```bash
# 1. 根据 OpenSpec 分解任务
# 假设 change_id 对应 3 个任务

# 2. 创建 TASK 文件（使用模板）
for task_id in TASK-001 TASK-002 TASK-003; do
  cat > collaboration/tasks/${task_id}.md << EOF
---
task_id: ${task_id}
change_id: <change_id>
status: pending
assignee: <agent>
reviewer: <reviewer>
acceptance_commands:
  - "pytest ..."
result_file: collaboration/results/RESULT-${task_id}.md
---

# 任务：[标题]

## 背景
[引用 OpenSpec，不重复 Why]

## 目标
[本任务的具体目标]

## 验收标准
- [ ] 标准1
- [ ] 标准2
EOF
done

# 3. 验证契约
python3 -m ai_collab.cli tasks validate-contract --scope active --strict

# 4. 等待确认
# （人工确认任务分配是否合理）
```

**输出**：
- 多个 `TASK-*.md` 文件
- 契约验证通过报告

---

### 阶段 3：三级派单（执行）

```bash
# 1. 为每个 TASK 创建 payload
for task_id in TASK-001 TASK-002 TASK-003; do
  python3 -m ai_collab.cli dispatch \
    --task-id ${task_id} \
    --assignee <agent> \
    --dry-run  # 先预览
done

# 2. 确认无误后正式派单
python3 -m ai_collab.cli dispatch --task-id TASK-001 --assignee <agent>

# 3. 监控执行状态
python3 -m ai_collab.cli status --scope active

# 4. 处理过程中的调整
# 如需调整：
python3 -m ai_collab.cli tasks update \
  --task-id TASK-001 \
  --assignee <new_agent> \
  --reason "原执行者忙碌"
```

**输出**：
- Payload 文件
- 状态记录
- 调整日志

---

### 阶段 4：验收与归档

```bash
# 1. 执行验收命令
pytest ... --cov

# 2. 创建 RESULT 文件
cat > collaboration/results/RESULT-TASK-001.md << 'EOF'
# 结果报告

## 验收命令执行
...

## Coverage Report
...

## 完成时间
...
EOF

# 3. 归档 OpenSpec
openspec archive <change_id> --yes

# 4. 更新 specs/
# （自动合并 delta 到正式 spec）
```

---

## 五、模板与检查清单

### 一级模板

```markdown
# Change Proposal: [标题]

## Why
[为什么需要这个变更 - 业务价值、技术债、风险]

## What Changes
[具体变更内容 - 新增/修改/删除]

## Impact
- Affected specs: [受影响的 spec 列表]
- Affected code: [受影响的代码文件]
- 风险: [风险点和缓解措施]

---

## 验收标准（从 Spec 角度）
- [ ] 每个 Requirement 有 Scenario
- [ ] 使用 SHALL/MUST
- [ ] 场景覆盖边界情况
```

---

### 二级模板

```markdown
---
task_id: TASK-XXX-YYY-ZZZ
change_id: <一级 change_id>
status: pending
priority: P0/P1/P2
assignee: <agent>
reviewer: <reviewer>
primary_skill: <主要技能>
support_skills:
  - <辅助技能1>
  - <辅助技能2>
created_at: YYYY-MM-DDTHH:MM:SSZ
acceptance_commands:
  - "pytest ..."
  - "命令2 ..."
result_file: collaboration/results/RESULT-TASK-XXX-YYY-ZZZ.md
---

# 任务：[标题]

## 背景
引用一级 OpenSpec，不重复 Why。

## 目标
本任务的具体目标（一级的一部分）。

## 步骤
### Step 1: [步骤标题]
**命令**: ...
**验证**: ...

## 验收标准
- [ ] 标准1（对应一级 Spec 的 Scenario）
- [ ] 标准2

## 完成后回复
A.ACK|task=TASK-XXX-YYY-ZZZ|status=ok|result=描述
```

---

### 三级检查清单

**派单前检查**：
- [ ] 二级 TASK 已确认（assignee、acceptance_commands 确定）
- [ ] 一级 OpenSpec 已验证通过
- [ ] 无阻塞依赖（或已记录 blocker）

**派单内容检查**：
- [ ] payload 包含 task_id、assignee、acceptance_commands
- [ ] payload 格式正确（JSON 语法）
- [ ] 文件名符合规范（`payload_<agent>_latest.json`）

**调整记录检查**：
- [ ] 调整原因已记录
- [ ] 影响范围已评估
- [ ] 相关方已通知

---

## 六、经验总结

### 核心原则

1. **一级纯战略**：只回答"为什么做""做什么"，不涉及"谁做""怎么做"
2. **二级承上启下**：引用一级，分解为可执行单元，分配资源
3. **三级动态响应**：执行中调整，但所有变更留痕

### 层次间关系

```
一级 ←→ 二级：change_id 绑定
二级 ←→ 三级：task_id 绑定
一级 ←→ 三级：不直接关联（通过二级间接关联）
```

### 回溯原则

- 三级发现一级问题 → 提交新 OpenSpec 修正（不直接改一级）
- 三级发现二级问题 → 记录调整原因后修改二级
- 二级发现一级问题 → 提交新 OpenSpec 修正

---

## 七、本次实践复盘

### 做对的
- ✅ 创建了一级 OpenSpec（proposal.md + spec.md）
- ✅ 定义了清晰的验收标准
- ✅ 使用了 ai-collab-base 的现有机制

### 做错的
- ❌ 一级 proposal.md 包含了任务分解和时间线（应在二级）
- ❌ 立即创建了三级 payload（应等二级确认）
- ❌ TASK 文件重复了一级内容

### 下次改进
- 严格分离三级层次
- 每一级完成后等待确认，再进入下一级
- 使用模板和检查清单，避免遗漏

---

## 八、参考文档

- OpenSpec 工作流：`collaboration/guides/OPENSPEC_PACK_MARKET_WORKFLOW.md`
- 任务契约手册：`collaboration/guides/TASK_CONTRACT_OPS_PLAYBOOK.md`
- CodeArts 派单指南：`collaboration/guides/CODEARTS_DISPATCH_GUIDE.md`
- 协作协议：`collaboration/PROTOCOL.md`

---

**更新日期**: 2026-06-01
**维护者**: CodeArts (Huawei Cloud)
**状态**: 已验证
