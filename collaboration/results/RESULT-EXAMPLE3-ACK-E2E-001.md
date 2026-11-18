# RESULT — 范例三端到端 ACK 流取证（TASK-EXAMPLE3-ACK-E2E-001）

> 执行日期：2026-11-18
> 执行者：claude_code（`orchestration detect` 中唯一 `connected` 的 provider）
> 目的：把 `docs/APPLICATION-EXAMPLES.md` 范例三从 **D1（组件级）** 推到 **D3（端到端留回执）**，
> 同时检验文档描述的四步骤是否真的能按序走通。
> 口径：本文件记录**实际输出**，不写预期输出。凡与文档或 PROTOCOL 不符处单列为发现。

- **状态**: completed

## 执行命令

```bash
# 步骤 1 角色与服务商
python3 -m ai_collab.cli orchestration detect
python3 -m ai_collab.cli orchestration status

# 步骤 2 注册与派发
python3 -m ai_collab.cli tasks register \
  --task-id TASK-EXAMPLE3-ACK-E2E-001 --ai claude_code \
  --description "..." \
  --result-file collaboration/results/RESULT-EXAMPLE3-ACK-E2E-001.md --apply
python3 -m ai_collab.cli dispatch --include-pending

# 步骤 3 显式 ACK
python3 -m ai_collab.cli ack --task-id TASK-EXAMPLE3-ACK-E2E-001 --ai claude_code --status ok

# 步骤 4 回执（第一次，失败；补 testing 后重跑）
python3 -m ai_collab.cli receipt
python3 -m ai_collab.cli tasks update --task-id TASK-EXAMPLE3-ACK-E2E-001 --status testing --apply
python3 -m ai_collab.cli receipt

# 步骤 4 看门狗 + 一致性审计
python3 -m ai_collab.cli ack-watchdog
python3 -m ai_collab.cli tasks audit-result-consistency
```

## 验证结果

### 测试结论

**范例三的协议链路可按序走通并留下可复核回执；本轮补上取证文档、纠正一处误判、并跑出 4 处偏差。
需要明确：它的实质档位在本次之前已是 D3（见 F5 自纠），本轮不是「从 D1 推到 D3」。**
具体见 §发现 F1–F8 与 §收口。

逐步骤判定：

| 步骤 | 文档说 | 实测 | 判定 |
|---|---|---|---|
| 1 角色与服务商 | `detect` + `status` | 可执行，`active` / `multi_agent` | ✅ 成立 |
| 2 注册与派发 | `tasks register` + `dispatch` | `candidate_count=1, dispatched_count=1` | ✅ 成立 |
| 3 显式 ACK | `ack --task-id ... --ai ... --status ok` | 输出 `X.ACK|task=...|status=ok|result=...` | ⚠️ 成立，但前缀与文档 provider 表不符（F1） |
| 4 回执 | `receipt` | 直接跑 **0 候选**，缺 `--status testing` 一步（F2） | ❌ 文档缺步 |

## 发现

### F1〔文档口径〕ACK 前缀是两个命名空间，文档没说谁优先

- 文档原文（`docs/APPLICATION-EXAMPLES.md:205-206`）：
  「前缀 P 由角色/绑定 provider 派生（provider 兜底表: claude_code→C、codearts_agent→A、codex→O）」
- 实测：`claude_code` 发出的 ACK 前缀是 **`X`**，不是 `C`。
- 根因：`ai_collab/role_prefix.py:30` 自己写着——
  「`X.ACK` 既可能是 codex 的 ACK，也可能是 claude_code 当 AGENT_ARCH 的 ACK」。
  实际派生走 **`assignee_role`（AGENT_ARCH → X.RUN）**，provider 表只在无 role 时兜底。
- 影响：读者照文档 provider 表去 grep `C.ACK` 找 claude_code 的 ACK，**会找不到**。
- 性质：文档表述歧义，不是代码缺陷。

### F2〔文档口径〕范例三四步骤缺「转 testing」，按文档原文走不到回执

- `scripts/agent_receipt_bridge.py:279`：`if task.get("status") != "testing": continue`
- `dispatch` 只写派发状态（`agent_dispatch_state.json`），**不改 `collaboration_state.json` 的任务状态**。
- 因此按文档原文执行，`receipt` 永远 0 候选（实测第一次 `candidate_count: 0`）。
- 缺的步骤：`tasks update --task-id <ID> --status testing`。
- 性质：文档步骤缺项，会让人误判「回执功能坏了」。

### F3〔行为边界〕`ack` 不校验产物文件是否存在

- 对 `TASK-EXAMPLE3-ACK-E2E-002` 声明一个不存在的 `result` 路径，ACK 仍输出成功行：
  `X.ACK|task=TASK-EXAMPLE3-ACK-E2E-002|status=ok|result=collaboration/results/RESULT-EXAMPLE3-ACK-E2E-002-DOES-NOT-EXIST.md`
- 即 **ACK 是「声明」，不是「验收」**。产物存在性由后续 `check_result_file` 与一致性审计把关。
- 文档未说明这一分工，容易让人以为 ACK 成功就等于交付成功。

### F4〔配置矛盾〕主执行者绑定在 unavailable 的 provider 上

- `orchestration status`：`AGENT_EXEC → codearts_agent  [主执行者]`
- `orchestration detect`：`codearts_agent: unavailable`
- 即「主执行者」角色指向一个检测不通的服务商。本轮走 AGENT_ARCH 路径未被阻塞；
  但若按角色表派给 AGENT_EXEC，会派给不可用通道。**需用户裁定**。

### F5〔自纠〕此前「历史任务无身份留痕」的判断是错的

- **原判断（已作废）**：「`logs/collaboration_state.json` 18 条 `completed` 任务的 `ai` 字段全为 `null`，
  说明历史 ACK 从未带 provider 身份，无法反查谁做的。」
- **错在哪**：任务对象里**根本没有 `ai` 这个字段**。真名是 `ai_type`。用 `t.get('ai')` 查一个不存在的键，
  静默返回 `None`，而 `None` 被我读成了「没有身份」——于是一个不存在的缺陷被造出来了。
- **磁盘事实**（2026-11-18 复核）：

  ```
  collaboration_state.json 20 条任务：ai_type 非空 20/20（claude_code 13 / codearts_agent 7）
                                     assignee 非空 20/20、assignee_role 非空 20/20
                                     `'ai'` 键存在性：False（全仓无此键）
  agent_ack_bridge_state.json 20 条：source=cli-ack 20/20、bridged_at 20/20、
                                     receipt_completed_at 20/20、result_file 20/20
  最早 bridged_at = 2026-10-23T10:17:04
  ```

- **修正后的结论**：范例三的历史闭环**早就完整**（注册→派发→cli-ack→回执→产物），
  最早可追到 2026-10-23。因此它的实质档位在本次之前**已经是 D3**，
  不是本轮「从 D1 推到 D3」。本轮的真正贡献是：① 产出一份**按文档步骤可复现**的取证文档
  （此前 18 条只有各自的结果文件，没有一份把四步骤串起来的取证明细）；
  ② 因为真按文档走，才暴露出文档缺步（F2）与门禁互斥（F6/F7）等在组件级测试里看不见的问题。
- **方法教训**：查状态前先确认字段真名。`dict.get()` 对不存在的键不报错，
  会把「字段名写错」伪装成「数据为空」，这是 disk-truth 核对里最隐蔽的一类假阴性
  （与 N40 的「文件在但没入库」不同：这次是「键在但名字错」）。

### F6〔门禁互斥·需立账〕PROTOCOL §7.4 合规的结果文件会被回执桥判 invalid 〔台账 N41，已修 closed〕

> **已修（2026-11-18，查 N41）**：两处判据已收敛为 `ai_collab/result_file_contract.py` 一份实现，
> 判据从「字面 `## ` 子串匹配」改为「标题语义匹配」（H2–H4、允许编号、允许复合标题、
> 要求以同义词开头）。下方记录保留发现时的原始状态以便追溯；**现状以 §F6-F7 修复回填 为准**。
> 修复后四形态探针两处门禁结论完全一致：A/B PASS、C/D FAIL(回滚)。

- `collaboration/PROTOCOL.md:413-420` 强制四段：`## 执行命令` / `## 验证结果` / `## 风险` / `## 回滚`，
  且规定「验证结果」**须含「测试结论」小节**（subsection，非 H2 标题）。
- `scripts/agent_receipt_bridge.py:122` 却要求字面 `REQUIRED_SECTIONS = ("## 执行命令", "## 测试结论", "## 风险")`。
- `scripts/agent_dispatch_bridge.py:266` 给执行者的指令只提四段，**未提「测试结论」小节**。
- 探针实测（三种文件形态）：

  | 结果文件 | 回执桥 | state_manager |
  |---|---|---|
  | A：四段齐全、无「测试结论」小节 | **FAIL** `missing ['## 测试结论']` | PASS |
  | B：四段 + `### 测试结论` 小节 | PASS | PASS |
  | C：只有三标题、**缺 `## 回滚`** | PASS | PASS |

- 结论：**照派单指令写的结果文件（形态 A）会在最后一步被拦**；而缺失 PROTOCOL 强制段落的
  文件（形态 C）两处门禁都放行。两处门禁判据不一致，且方向相反。

### F7〔门禁缺口〕`## 回滚` 是强制段，但零执行 〔台账 N41，已修 closed〕

> **已修（2026-11-18）**：`回滚` 已从「风险」的替代词提升为**独立必填组**。
> 缺 `## 回滚` 现在两处门禁都会报 `missing sections=[回滚]`，由
> `tests/unit/test_result_file_contract.py::test_missing_rollback_is_reported` 守住；
> 把回滚组从权威表删掉的变异会被该用例杀死（已验证）。

- 形态 C（无 `## 回滚`）在 `check_result_file` 与 `TASK_RESULT_REQUIRED_SECTION_GROUPS` 双双通过。
- `state_manager.py:348-352` 的第三组是 `("风险", "回滚", "risk")`——「回滚」只是「风险」的**替代词**，
  写了「风险」就算满足，无需单列「回滚」。
- 即 PROTOCOL §7.4 的第四段**没有任何门禁强制**。

### F6-F7 修复回填（2026-11-18，N41 closed）

两处门禁已收敛为一份判据 `ai_collab/result_file_contract.py`：

| 项 | 修复前 | 修复后 |
|---|---|---|
| 判据形态 | 回执桥：字面 `## ` 子串；state_manager：三组替代词 | 两侧同一份 `SECTION_GROUPS`，标题语义匹配 |
| `## 4. 执行命令` | 匹配不上（回执桥） | ✅ 允许前导编号 |
| `## 风险与回滚` | 只满足风险 | ✅ 同时满足两组 |
| `### 关于回滚的说明` | 会顶替真正的回滚段 | ✅ 不命中（须以同义词**开头**） |
| `回滚` | 只是「风险」的替代词，零强制 | ✅ 独立必填组 |
| 副本漂移 | 无人守 | ✅ `test_result_file_contract.py` 逐字对账 + 行为等价 |

验证证据：

- 四形态探针两处门禁结论**完全一致**：A（合规、测试结论为 H3 小节）/ B（编号 + 复合）PASS；
  C（缺回滚）/ D（旧回执桥形态，缺验证结果与回滚）FAIL `[回滚]`。
- 三条变异全部被杀死：M1 回执桥副本改一个同义词 / M2 权威侧删回滚组 / M3 判据退化回子串匹配。
- 顺带发现并修掉一处**测试夹具自身不合规**：`test_agent_receipt_bridge.py` 的「有效结果文件」
  原本只有三段、缺 `## 回滚`——它恰好证明旧判据把强制段放行了（一份不合规样本被当成有效样本用）。
- blast radius 实测：在册 20 条任务 20/20 齐备（零破坏）；47 份历史结果文件中 16 份不合规，
  但均未挂在任何在册任务上，不会被校验。

### F8〔可达性〕一致性审计的 `missing_result_file` 分支正常路径不可达 〔台账 N42，已修 closed〕

> **已修（2026-11-18，查 N42）**：审计的产物要求改为按状态分流——
> `completed` 必须交产物；`failed`/`blocked` 允许无产物但必须留原因；`cancelled` 不要求。
> 同时新增一条**不依赖终态**的扫描：任务停在非终态、但已有 `status=ok` 的显式 ACK、
> 产物却不存在 ⇒ 报 `ack_without_artifact`。这正是下方记的「双网漏掉」那个盲区。
> 下面保留发现时的原始记录。



- 尝试把缺产物的 `TASK-EXAMPLE3-ACK-E2E-002` 直接写终态：
  `错误: 任务结果门禁失败: TASK-EXAMPLE3-ACK-E2E-002; result_file not found: ...`
- 写入门禁**阻止**缺产物任务进入终态 ⇒ 正常情况下不存在「终态且缺产物」的任务。
- 该分支只在**事后删除产物**时可达（如清理误删）。已用「同一任务删后恢复」实验验证
  该分支确实活着、不是死代码（见 §收口）。

## 风险

1. ~~**F6/F7 会让合规交付在最后一步被拦**~~ —— **已修（N41 closed）**：判据已收敛，
   四形态探针两处门禁结论一致，缺回滚两处都报。残余风险变为「历史结果文件中有 16 份不合规」，
   但它们未挂在在册任务上，不会被校验。
2. **F2 会让首次跑范例三的人以为回执坏了**，实际只是漏了状态流转。
3. **F1 会让审计者按文档 grep `C.ACK` 找不到任何 claude_code 的 ACK**，误判「没有 ACK」。
4. **F4 的绑定矛盾**会在真正启用三 agent 协作时直接踩坑（派给 unavailable 通道）。
5. 本轮 AGENT_ARCH 与 AGENT_TEST 都由**同一执行者**扮演，未验证「真实多 agent 并发」场景。
6. 一致性审计的 `consistent` 只说明「产物在」，不说明「产物内容合格」。

## 回滚

本任务**不修改任何受版本控制的业务代码或配置**。新增/变更的只有：

| 文件 | 处置 |
|---|---|
| `docs/EXAMPLE-ACCEPTANCE-MATRIX.md` | 新增文档，回滚＝删除该文件 |
| `docs/APPLICATION-EXAMPLES.md` | 仅在 §总结 加一段指针注释，回滚＝`git checkout -- docs/APPLICATION-EXAMPLES.md` |
| `collaboration/results/RESULT-EXAMPLE3-ACK-E2E-001.md` | 本文件，回滚＝删除 |
| `known_gaps.json` | N41 已关闭、N42/N43/N44 已登记，回滚＝还原该文件 |
| `ai_collab/result_file_contract.py` / `tests/unit/test_result_file_contract.py` | N41 新增实现与绊线，回滚＝删除 |
| `ai_collab/state_manager.py` / `scripts/agent_receipt_bridge.py` / `scripts/agent_dispatch_bridge.py` / `collaboration/PROTOCOL.md` | N41 判据收敛，回滚＝`git checkout --` 这四个文件 |
| `logs/*.json`（协作状态） | **未跟踪**，不进版本库，无需回滚 |

回滚命令：

```bash
git checkout -- docs/APPLICATION-EXAMPLES.md known_gaps.json
rm -f docs/EXAMPLE-ACCEPTANCE-MATRIX.md collaboration/results/RESULT-EXAMPLE3-ACK-E2E-001.md
```

## 口径声明

- 本文件是**机器判定 + 人工核对**的混合产物：命令输出为原始粘贴，发现条目均给出文件与行号。
- `status=ok` 只证明「协议链路按序走通」，**不证明**范例三的业务目的（真实三角色协作开发）已发生。
- 与 `RESULT-L2-ACTIVE5-NOV18-2026-11-18.md` §4 口径一致：机器判定 ≠ 人工验收。

## 收口

### 回执（补 testing 后）

```
$ python3 -m ai_collab.cli tasks update --task-id TASK-EXAMPLE3-ACK-E2E-001 --status testing --apply
任务状态已更新: TASK-EXAMPLE3-ACK-E2E-001 -> testing

$ python3 -m ai_collab.cli receipt
candidate_count: 2
completed_count: 1
completed_tasks: ["TASK-EXAMPLE3-ACK-E2E-001"]
state_updated: true
errors: [{ task_id: TASK-EXAMPLE3-ACK-E2E-002, error: "result_file not found: ...", category: result_file_not_found }]
```

`logs/collaboration_state.json`：`TASK-EXAMPLE3-ACK-E2E-001` → `completed`，
`completed_at = 2026-11-18T16:29:17`。

> 首次 `receipt` 因结果文件缺 `## 测试结论` 被拒（`result_file_invalid`），
> 这正是 F6。本文件补上 `### 测试结论` 小节后才通过——`### 测试结论` 能命中字面
> `## 测试结论` 是因为子串匹配，属巧合。

### 一致性审计（三次，同一任务三种结论）

| 次序 | 操作 | audited | consistent | mismatch | missing_result | 判定 |
|---|---|---|---|---|---|---|
| 1 | 产物在，状态行写错为 `testing` | 19 | 18 | **1** | 0 | `terminal_status_mismatch`（审计真的在比对状态行） |
| 2 | 状态行改为 `completed` | 19 | **19** | 0 | 0 | 全绿 |
| 3 | 临时移走产物 | 19 | 18 | 0 | **1** | `missing_result_file`（分支活着） |
| 4 | 恢复产物 | 19 | **19** | 0 | 0 | 全绿，且 `cmp` 确认恢复内容与备份 **IDENTICAL** |

第 1 与第 3 次是**必要的反证**：若无这两次，第 2 次的 `consistent=19` 不能排除
「审计根本没在检查」。这与变异检查同理——门禁必须能红，绿才有意义。

### 看门狗

```
$ python3 -c "from pathlib import Path; from ai_collab.ack_watchdog import run_ack_watchdog;
              print(run_ack_watchdog(workspace=Path('.'), dry_run=False))"
generated_at: 2026-11-18T16:31:05
mode: apply   threshold_seconds: 120
candidate_count: 0   redispatched_count: 0   alerted_count: 0   error_count: 0
```

`candidate_count: 0` 是**正确结果**——001 已 ACK 并 completed，002 已 ACK，两者按设计都不进候选。
但这同时暴露 F8：002 那种「已 ACK 却无产物」的任务被看门狗排除，也不被审计扫到。

### 档位判定（含对本轮初始判断的自纠）

**范例三 = D3。但这个 D3 早于本轮就成立，不是本轮挣来的。**

| 判断来源 | 结论 | 状态 |
|---|---|---|
| 本轮初始判断（基于 F5 原始版本） | D1，理由「18 条任务 ai 字段全 null ⇒ 无身份留痕」 | ❌ **作废**，`ai` 字段不存在，查错键 |
| 复核后的事实 | 18 条历史任务早已完整闭环（`source=cli-ack` + `bridged_at` + `receipt_completed_at` + 产物齐全），最早 2026-10-23 | ✅ 采信 |

本轮**真正**的贡献不是提档，而是三件事：

1. 产出**按文档步骤可复现**的取证文档（此前 18 条只有各自结果文件，没有串起四步的明细）；
2. 因为真按文档走，暴露了组件级测试看不见的 4 处偏差（F2 文档缺步、F6/F7 门禁互斥、F8 双网盲区）；
3. 自纠一处由字段名写错造成的假缺陷（F5）。

反证实验（审计三次会红、`cmp IDENTICAL`）的价值不因档位未变而减少——
它回答的是「这套门禁是不是空转」，与「范例排第几档」是两个问题。

### 附带产出

| 产物 | 说明 |
|---|---|
| `docs/EXAMPLE-ACCEPTANCE-MATRIX.md` | 四范例验收矩阵（D0–D3 四档），本任务的直接交付物 |
| `collaboration/results/RESULT-EXAMPLE3-ACK-E2E-002-NEGATIVE-CONTROL.md` | 负向对照的自述文件（任务已 cancelled） |
| `known_gaps.json` N41 | 门禁互斥 + 回滚零执行，**已随本轮修复关闭**（见 §F6-F7 修复回填） |
| `known_gaps.json` N42 / N44 | 本次新发现的两条待修缺陷（open，等裁定） |
| `ai_collab/result_file_contract.py` | N41 的唯一判据实现（新） |
| `tests/unit/test_result_file_contract.py` | N41 绊线：两侧逐字对账 + 行为等价 + 三处变异锚 |
| `known_gaps.json` N43 | 范例三文档缺步与前缀歧义，**已随本任务修复并关闭** |

### 未做（诚实边界）

- 未验证「真实多 agent 并发」：AGENT_ARCH 与 AGENT_TEST 由同一执行者扮演。
- 未验证看门狗的超阈告警分支：需构造一个超 120 秒未 ACK 的任务，本轮未造。
- 未修 F4/F8：已登记 N42/N44，等裁定。（F6/F7 已修，见 §F6-F7 修复回填。）
