# RESULT-PREFIX-DERIVATION-2026-10-23

**任务**：`TASK-P1-PREFIX-DERIVATION-001`
**执行方**：Claude Code（AGENT_ARCH）
**状态**：completed

---

## 一、纠正：上一轮开发日志写错了缺陷位置

上一轮（开发日志 §18.3）留下的后续动作写的是：

> **修派生路径分叉（真缺陷）**：`ai_collab/cli/_cli_main.py` 的 `cmd_ack` 已经
> `manager.get_task(task_id)` 拿得到 `assignee_role`，改成与 `resolve_hints` 同源
> （角色优先）即可。

**这条描述是错的。** `git log -L` 显示：CLI ACK 路径**早在 `229062d`
（2026-10-22 命名空间收敛那次提交）就已经是角色优先**了 ——

```python
# ai_collab/cli/_cli_main.py:1130,1143-1150（229062d 引入，至今未变）
assignee_role = str(task.get("assignee_role") or "").strip()
ack_line = build_ack_line(..., assignee_role=assignee_role or None, workspace=Path(workspace))
```

当时的判断错在：看了 `build_ack_line()` 的**默认参数**（`assignee_role=None` ⇒
provider 优先），就推断 CLI 路径也是 provider 优先，没有去核对调用点是否传了角色。

**真证在数据里**：`logs/agent_ack_bridge_state.json` 的三条实测记录（修复前）：

| task_id | assignee | 工单角色 | 记录的 ACK 行 | 应为 |
|---|---|---|---|---|
| TASK-P1-GOV-CONVERGE-001 | claude_code | AGENT_ARCH | `C.ACK\|...` | `X.ACK\|...` |
| TASK-P1-PREFIX-DISJOINT-001 | claude_code | AGENT_ARCH | `C.ACK\|...` | `X.ACK\|...` |
| TASK-P0-CONSENSUS-ENGINE-001 | codearts_agent | AGENT_EXEC | `A.ACK\|...`，但 result 指向已删除的 `hermes_target/` | 前缀对、路径错 |

三条记录的 `assignee_role` 字段**全是 `None`** —— 角色在写入链路里被整个丢掉了，
这才是分叉的来源。

## 二、根因：三处，不是三处「同一件事」

| # | 位置 | 缺陷 | 影响 |
|---|---|---|---|
| **R1** | `scripts/agent_receipt_bridge.py::ack_prefix_for()` | 纯 provider 优先，**完全不认识角色** | 桥接路径永远给不出 `X.ACK` |
| **R2** | `scripts/agent_receipt_bridge.py::run_receipt()` 收口写记录 | 用 provider 前缀拼 `ack_line`；记录里**不写** `assignee_role` | 把 CLI 已经写好的 `X.ACK` **覆盖回** `C.ACK`，并抹掉角色 |
| **R3** | `ai_collab/ack_protocol.py::upsert_ack_bridge_item()` | 用角色算了 `ack_line` 的前缀，但**记录里不落** `assignee_role` | 下一次只拿到 provider 的写入会把前缀**降级**回去 |
| R4（次要） | `ai_collab/cli/_cli_main.py::cmd_ack()` 工单不存在分支 | 不复用历史 ACK 记录里的角色 | 只能退到 provider 字母 |

R2 是**覆盖者**（它把别处写对的行改错），R3 是**丢失者**（它让下一次写入退化）。
R1 是**产生者**。三处缺一不可 —— 只修 R1 的话，R2 仍会用错的前缀写回。

### 为什么"AGENT_EXEC 与 AGENT_TEST 看不出来"

`AGENT_EXEC(codearts_agent→A)` 与 `AGENT_TEST(claude_code→C)` 两条路径**巧合一致**
（provider 兜底字母恰好等于该 provider 所占席位的角色字母）。
**只有 `AGENT_ARCH(claude_code)` 这一格分叉** —— 它的角色字母是 `X`，
provider 兜底字母是 `C`。所以这个 bug 在实测数据里只表现为"两个 AGENT_ARCH 工单的
ACK 行是 `C.ACK`"，很容易被当成"claude_code 的正常前缀"而放过。

## 三、改动

### 3.1 `scripts/agent_receipt_bridge.py`

- `ack_prefix_for()` 改为**角色优先**：新增 `assignee_role` / `workspace` 参数，
  解析器指向 `ai_collab.role_prefix.resolve_ack_prefix`（前缀映射的**单一事实源**）。
  本脚本刻意不依赖 `ai_collab` 包，故把仓库根加进 `sys.path`，
  import 失败时退回本地硬编码表（与 `ai_collab/ack_protocol.py::_ACK_PREFIX` 一致，
  由 `tests/unit/test_ack_prefix_consistency.py` 强制同步）。
- 新增 `_prefix_workspace()`：**只选已经存在编排配置的目录**做解析输入。
  原因：`OrchestrationConfig.load()` 在找不到配置时会把模板 **copy 进目标目录** ——
  回执桥接只想「读前缀」，不该在别人的工作区里落文件。
- 收口写记录时改用角色前缀，并**写入 `assignee_role`**。

### 3.2 `ai_collab/ack_protocol.py`

- `upsert_ack_bridge_item()`：把 `assignee_role` **落进记录**；
  调用方没带角色时**保留记录里已有的角色**（不让后续的 provider-only 写入降级前缀）。

### 3.3 `ai_collab/cli/_cli_main.py`

- `cmd_ack()` 工单不存在分支：复用历史 ACK 记录里的 `assignee_role`。

### 3.4 附带修复：`scripts/codearts_bridge_deliver.py::_remove_from_cron_store()`

上一轮僵尸 cron 文件级清理里发现的**锁纪律缺陷**（与 ACK 无关，但同属"后续工作"）：

| 缺陷 | 后果 |
|---|---|
| `lock_path.exists()` 只**检测**不获取，`finally` 里却 `unlink()` 掉 | **删掉 kernel 自己持有的锁** —— kernel 会以为自己没在写，与本进程并发写同一份存储 |
| 注释写「自己创建过就清掉」，代码判断的却是「存在」 | 注释与实现不符（违反「commit message 不撒谎」原则） |
| 临时文件名固定 `scheduled_tasks.json.tmp` | 与 kernel 自己的临时文件可能撞名 |

修法：**只读锁、绝不删锁**；检测到锁存在时重新读一次存储再写（压缩「读-写」窗口，
避免用陈旧快照覆盖 kernel 刚加的任务）；临时文件名带 pid；如实上报 `lock_conflict`。

## 四、不变量测试（新增 22 条）

### 4.1 `tests/unit/test_ack_prefix_derivation.py`（新建，18 条）

| 测试 | 守住的规则 |
|---|---|
| `test_cli_and_bridge_derive_the_same_prefix`（4 参数化） | 两条派生路径对同一 (provider, role) 给出**同一个前缀** |
| `test_bridge_prefix_is_role_first`（4 参数化） | 带角色取角色字母；不带才退 provider |
| `test_bridge_prefix_falls_back_to_provider_without_role`（3 参数化） | 无角色时行为不回归 |
| `test_upsert_ack_bridge_item_persists_assignee_role` | 角色**落进记录** |
| `test_upsert_ack_bridge_item_preserves_existing_role` | 后续 provider-only 写入**不得抹掉**已知角色 |
| `test_cmd_ack_uses_role_prefix_for_agent_arch` | CLI 路径角色优先 |
| `test_cmd_ack_falls_back_to_provider_prefix_without_role` | CLI 路径无角色时不回归 |
| `test_cmd_ack_task_not_found_reuses_role_from_history` | 工单不在状态机里时复用历史角色 |
| `test_receipt_bridge_records_role_prefixed_ack_line` | 端到端：收口后记录是 `X.ACK` 且角色没丢 |
| `test_receipt_bridge_does_not_create_config_in_foreign_workspace` | 桥接**不在别人的工作区落配置模板** |

**反向验证**（把三处源码改动 stash 掉后重跑）：**16 failed / 2 passed** ——
即这批测试确实在守真缺陷，不是摆设。

### 4.2 `tests/unit/test_codearts_bridge_deliver.py`（新增 4 条）

| 测试 | 守住的规则 |
|---|---|
| `test_remove_from_cron_store_never_deletes_kernel_lock` | **绝不删 kernel 的锁文件** |
| `test_remove_from_cron_store_reports_lock_conflict` | 锁冲突如实上报 |
| `test_remove_from_cron_store_reports_no_lock_conflict` | 无冲突时不误报 |
| `test_remove_from_cron_store_rereads_store_after_lock_conflict` | 锁冲突后重读，kernel 期间加的任务不被覆盖 |
| `test_remove_from_cron_store_leaves_no_temp_file` | 不留临时文件垃圾 |

**反向验证**（stash 掉 `codearts_bridge_deliver.py` 的改动后重跑）：4 failed，
且 `never_deletes_kernel_lock` 的失败原因是
`AssertionError: 不能删除 kernel 自己持有的锁文件` —— **正是那个缺陷本身**。

## 五、本地 ACK 记录修复

修复后用**修好的 CLI 路径**重发三条 ACK（不是手工改 JSON）：

| task_id | 修复前 | 修复后 |
|---|---|---|
| TASK-P1-GOV-CONVERGE-001 | `C.ACK\|...`，role=None | `X.ACK\|...`，role=AGENT_ARCH |
| TASK-P1-PREFIX-DISJOINT-001 | `C.ACK\|...`，role=None | `X.ACK\|...`，role=AGENT_ARCH |
| TASK-P0-CONSENSUS-ENGINE-001 | `A.ACK\|...`，result 指向已删除的 `hermes_target/` | `A.ACK\|...`，result 指向 `collaboration/results/` |

`logs/` 是 gitignore 的本地控制面状态，**不入库**；原文件已备份到
`/tmp/agent_ack_bridge_state.json.bak-20261023`。

## 六、§18.3 剩余两项的处置

| 项 | 处置 | 理由 |
|---|---|---|
| ② 给 X 一个语义锚点（`AR.RUN` 别名） | **不做** | 零功能收益：前缀是标签、解析是数据驱动的（`get_role_for_command` 读 config），X 与 D 功能等价。要让别名生效必须改 `get_command_prefix_for_role()` 的「标准前缀优先于 custom」优先级 —— 那是**改一个 6 处副本都在用的公共函数**，收益 0、风险不为 0。字母池不重叠已由 11 条不变量测试锁住，语义锚点不是安全缺口 |
| ③ 不换字母、不重写历史记录 | **遵守** | 上一轮裁决：换字母要付 100% 副本漂移风险换 0 收益，且同类事故已发生一次（`229062d` 只改 4 份副本里的 1 份 ⇒ 冷启动拿回倒挂映射）。历史 RESULT/工单里的 X 记录**只加注、不重写** |

## 执行命令

```bash
# 验收命令（与工单 acceptance_commands 逐字一致，回执桥接会做子串校验）
python3 -m pytest tests/unit/test_ack_prefix_derivation.py tests/unit/test_ack_prefix_consistency.py tests/unit/test_agent_receipt_bridge.py tests/unit/test_cli_ack.py -q
python3 -m pytest tests/unit/test_codearts_bridge_deliver.py -q
python3 -m pytest tests/ -q
python3 -m ruff check ai_collab/ scripts/

# 补充验证
python3 -m pytest tests/unit --cov=ai_collab --cov-report=term -q
python3 -m mypy ai_collab/
```

## 测试结论

| 项 | 结果 |
|---|---|
| 派生路径 + 桥接 + CLI ACK 相关 | **100 passed**（4 个文件） |
| 新增不变量测试 | **22 条**（18 条派生路径 + 4 条锁纪律） |
| **反向验证（stash 掉修复后）** | 派生路径 **16 failed** / 锁纪律 **4 failed** —— 测试确实在守真缺陷 |
| 全量测试 | **2835 passed, 6 skipped**（2835 = 修复前 2812 + 新增 22 + 1 条既有用例因记录字段变化而重算） |
| 覆盖率（`tests/unit` 口径） | **88%** ≥ 门禁 85% |
| ruff（`ai_collab/` `scripts/` + 两个测试文件） | **无新增问题** —— 与 HEAD 逐行 diff 唯一差异是 `codearts_bridge_deliver.py` 一条**既有** UP012 告警的行号位移（388→389） |
| mypy（`ai_collab/`） | **Success: no issues found in 100 source files** |
| 行为级复验 | `cli.cmd_ack` 对 AGENT_ARCH 工单发 `X.ACK`；桥接收口后记录为 `X.ACK` 且 `assignee_role=AGENT_ARCH` |
| 兼容性 | 仓库内**不存在「前缀 → provider」的反向查找**（全仓 grep 确认）；ACK 归属靠 `task_id` + `source`（`has_explicit_ack`）⇒ 前缀变更不影响归属判定 |

## 风险

| 风险 | 影响 | 处置 |
|---|---|---|
| **行为变更**：claude_code 的 AGENT_ARCH 工单 ACK 前缀由 `C.ACK` 变 `X.ACK` | 外部若硬编码匹配 `C.ACK` 会认不出 | 仓库内无前缀反查；ACK 归属靠 task_id。协议 §6.1 本就规定角色席位用 `X.ACK`，**改后才是与协议一致的** |
| 桥接路径开始 import `ai_collab` | 脚本被单独拷到别处执行时 import 失败 | `try/except` 退回本地硬编码表（行为退回到修复前的 provider 优先，但不崩） |
| `OrchestrationConfig.load()` 有写副作用（缺配置时 copy 模板） | 桥接可能在别人的工作区落文件 | 新增 `_prefix_workspace()`：只在**已存在**编排配置的目录上解析，否则用仓库根 |
| 记录里新增 `assignee_role` 字段 | 下游读该 JSON 的脚本若假设字段集封闭会受影响 | 全仓 grep 无此类消费者；字段是**新增**而非改名，旧读者忽略未知键即可 |
| cron 兜底删除改成"只读锁" | 若 kernel 的锁是陈旧的（进程已死但锁没清），本次写入会与 kernel 并发 | 锁冲突时**重读一次存储再写**（压缩窗口）并如实上报 `lock_conflict`；陈旧锁由 kernel 自己的新鲜度判定处理 |
| 临时文件名改为带 pid | 与 kernel 的临时文件不再撞名 | 更安全；kernel 的文件监听器若按目录通配可能看到该临时文件 —— 但修复前的固定名 `scheduled_tasks.json.tmp` 同样会被看到，风险等价 |

## 回滚

```bash
# 回滚本任务全部改动
git revert <本任务提交>

# 若只回滚 ACK 前缀派生修复（保留 cron 锁纪律修复）
#   - scripts/agent_receipt_bridge.py：ack_prefix_for 退回单参数 provider 优先；
#     收口写记录退回不写 assignee_role
#   - ai_collab/ack_protocol.py：upsert_ack_bridge_item 退回不落 assignee_role
#   - ai_collab/cli/_cli_main.py：cmd_ack 工单不存在分支退回不传角色

# 若只回滚 cron 锁纪律修复
#   - scripts/codearts_bridge_deliver.py::_remove_from_cron_store 退回旧版
#   ⚠️ 这会把「删掉 kernel 自己持有的锁」这个缺陷装回去，
#     且 test_remove_from_cron_store_never_deletes_kernel_lock 会失败
#     （预期行为：回滚等于撤销修复）。
```

回滚后需同步跑：
`python3 -m pytest tests/unit/test_ack_prefix_derivation.py tests/unit/test_codearts_bridge_deliver.py -q`
（不变量测试会失败 —— 因为它守的正是被回滚掉的那条规则，这是预期行为）。

---

## 配套产出

| 产出 | 位置 |
|---|---|
| 任务工单 | `collaboration/tasks/TASK-P1-PREFIX-DERIVATION-001.md` |
| 新增测试 | `tests/unit/test_ack_prefix_derivation.py`（新建 18 条） |
| 补强测试 | `tests/unit/test_codearts_bridge_deliver.py`（+4 条锁纪律） |
| 开发日志 | `logs/claude-code/2026-10/2026-10-22_codearts-collab-wiring.md` §19 |
| 记忆更新 | `~/.claude/projects/.../memory/ack-prefix-letter-pool.md`（纠正"CLI 路径 provider 优先"的错误记述） |

---

**相关提交**：（见 `git log --oneline -3`）
