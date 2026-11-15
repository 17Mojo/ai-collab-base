# Change Proposal: Close Governance Gaps

## Why

`restore-governance-enforcement`（已合入 `89160f1`，归档于 `2026-11-16`）把覆盖率门禁与账本
写入互斥修好了，但它在自己的结果报告里诚实登记了**三处仍未闭合的缺口**，三处都指向同一个
病根：门禁要么拿不到输入，要么拿到的输入无法核验。

1. **必读清单是裸自证，而且根本没有写入方。**
   `governance preflight` 的第一项检查读 `.ai_collab_session.json` 的
   `required_reads_acknowledged`，但全仓只有 `governance.py:597` 一处**读取**，没有任何
   模块写它（`sessions register` 写的是 `logs/session_registry_state.json`，另一个文件）。
   后果：该项在**任何** workspace 上恒 FAIL，五项门禁永久残废一项。更糟的是，即使有人
   手写这个文件，里面也只是一串路径名——它证明不了任何东西，因为文件改了声明照旧成立。

2. **会话级状态没有不受跟踪的落点。**
   `baselineCommit` / `sessionStartedAt` 是会话级状态，唯一落点是**受跟踪**的
   `.vscode/ai-collab.json`，没有覆盖机制。而 `detect_baseline_staleness()` 会把
   `baselineCommit..HEAD` 内被监视路径的任何提交计为 `violations`（`risk_level=high`、
   `allowed=false`）。于是「装备门禁」与「不给自己埋硬阻断」不可兼得——上一轮因此把
   这一项整条取消（见归档 tasks.md 的「显式取消」）。缺口不在门禁逻辑，在配置落点。

3. **开发日志写不进版本库。**
   `.gitignore:39` 是 `logs/` 目录级排除，git 不允许重新包含被排除目录下的文件，
   所以加 `!logs/governance-ledger.jsonl` 之类的取反规则无效（`git check-ignore -v`
   证实命中的是 `logs/` 这条目录规则）。`PROTOCOL §7.4` 要求的开发日志落点
   `logs/claude-code/` 因此永远不进库，等于「按规矩写了但没人能查」。

## What Changes

| # | 产物 | 内容 |
|---|------|------|
| A | `governance.ack_required_reads()` / `verify_required_reads()` | 必读清单声明升级为**可核验声明**：记录每个必读文件的 `sha256` + 会话标识 + 声明时间；核验时重算哈希，文档改过即判为过期（stale），要求重读 |
| A | `sessions ack-reads` CLI | 唯一写入方。写入 `.ai_collab_session.json`，不手改 |
| A | `preflight` 必读项改造 | 从「路径名是否在列表里」改为「哈希是否仍与磁盘一致」，并在过期时点名哪几个文件变了 |
| B | `.vscode/ai-collab.local.json` 覆盖层 | 不受跟踪的会话级配置落点，优先级高于 `ai-collab.json`；`guard_input_report()` 读合并结果 |
| B | `.gitignore` | 新增 `.vscode/ai-collab.local.json` 与 `.ai_collab_session.json`（两者都是会话级，不该进库） |
| C | `.gitignore` 拆分 | `logs/` → `logs/*` + `!logs/claude-code/` + `!logs/claude-code/**`，使开发日志可入库，其他 `logs/` 内容继续忽略 |

## Non-goals

- 不改 `PROTOCOL` / `AI-COLLABORATION-STANDARDS` 的**规则文本**（规则层不动，只补执行层）。
- 不改会话注册表语义（`assignee_provider → session_id + model_id` 仍属会话化 change）。
- 不追溯登记 11 月已合并的 PR。
- 不动 `logs/` 下其他子目录的忽略状态（`workspace_forensics` / `handoff` 等继续忽略）。

## Impact

- 行为变更：`preflight` 第一项从「永远 FAIL」变为可 PASS，但**要求声明带哈希**，
  手写的裸列表会被判为不合法（fail-closed），不是放宽。
- 行为变更：`.vscode/ai-collab.json` 的读取改为「tracked + local 合并」，
  已装备的仓库若存在 `local.json` 会以 local 为准（覆盖语义显式、可复核）。
- 仓库清洁度：`logs/claude-code/` 下的日志会开始出现在 `git status` 里，
  这是修复目标而非副作用；其余 `logs/` 内容不变。
- 本 change 自身的合入又是一个 merge commit，按上一轮建立的规则需要登记（流程已验证）。
