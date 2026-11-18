#!/usr/bin/env python3
"""N25 重开条件与机制（2026-11-15）：解释 + 落盘 + 回写 RESULT §28 / 工作日志。

只解释并登记机制，不重开 N25、不改台账状态、不碰 git。
"""
import json
import pathlib
import datetime

REPO = pathlib.Path("/Users/raymondna/Documents/AI-collab/ai-collab-base")
EVID = REPO / "collaboration/results/real-machine-runs/evidence"
RESULT = REPO / "collaboration/results/RESULT-L2-MULTIPLATFORM-2026-11-10.md"
LOG = pathlib.Path("/Users/raymondna/WorkBuddy/2026-11-04-12-09-59/.workbuddy/memory/2026-11-15.md")

kg = json.loads((REPO / "known_gaps.json").read_text())
gaps = kg.get("gaps") or kg.get("items") or []
n25 = next(x for x in gaps if x.get("id") == "N25")

mechanism = {
    "mode": "n25-reopen-conditions-and-mechanism-2026-11-15",
    "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "question": "解释下 N25 若需重开",
    "answerKind": "EXPLANATION_AND_MECHANISM_ONLY",
    "notAnInstructionToReopen": True,
    "currentState": {
        "status": n25.get("status"),
        "closed_at": n25.get("closed_at"),
        "closureType": (n25.get("closure") or {}).get("type"),
        "evidenceCount": len(n25.get("appended_evidence", [])),
        "recharacterized": bool(n25.get("recharacterization")),
        "ledgerCounts": {s: sum(1 for x in gaps if x.get("status") == s) for s in ("open", "closed", "wontfix")},
    },
    "whatClosedMeans": [
        "结案理由 = 原始观察对象已重新归因、墙不复现、命题不可判定",
        "不是验证通过（A/B 判据从未成立）",
        "不是『边界有效』，也不是『边界无效』",
        "不是『长会话撞墙已根治』",
        "F1 等待判据修复 / F2 会话入口可达 / ab4 B 组硬判据 2/2 / ab5 判无墙即停，这些事实不受关闭影响",
    ],
    "reopenTriggers": [
        {
            "id": "T1",
            "name": "出现新的可控自变量，且『墙』可被稳定复现",
            "isOnlyPathToDecidability": True,
            "machineConditions": [
                "A 组 stepsTotal==8 且 stepSuccess==7",
                "firstFailedStepId == 'step_8_output'",
                "失败错误含 Response timeout",
                "前 7 步全部成功且 sessionResets 为空",
                "截图人工视觉闸确认末条 AI 回复不是『服务出错啦，请稍后再试。』，且无登录墙 / 验证码",
                "同一平台相邻时间窗 B 组边界真执行且 available===true && messageCountAfter < messageCountBefore",
            ],
            "note": "这是唯一能让『会话边界解掉长会话撞墙』重新变成可判定命题的条件；§26 已证现有 A 组结构条件满足而墙 0 次出现。",
        },
        {
            "id": "T2",
            "name": "新证据推翻 §24 三条根因之一",
            "roots": ["F-D1 deepseek 原始超时是等待判据假超时", "F-D2 longcat 是站点随机报错", "F-D3 原始『长会话是变量』归因被隔离实验削弱"],
            "note": "须给出可复核的磁盘回执，不能只是重新解读旧证据。",
        },
        {
            "id": "T3",
            "name": "找到 §9.4 原始观察中可量化的第三变量",
            "examples": ["真实上下文 token 长度", "站点侧限流 / 并发窗口", "会话累积时长而非轮次"],
            "note": "必须能人为控制并写进新判据，否则仍是不可判定。",
        },
        {
            "id": "T4",
            "name": "审计或交付口径要求改结论性质",
            "note": "仍须附新证据；单纯改文案不构成重开理由。",
        },
    ],
    "notReopenReasons": [
        "想再跑一轮完整 4 轮 A/B —— §26 已证不改变自变量的盲跑不产生新证据",
        "台账里显示 closed 不好看 / 想留个 open 提醒",
        "把 F1 / F2 的真机验证挪用为『边界有效』的因果证据",
        "把『边界无效』当成结论",
        "仅重述旧证据、换一种措辞",
        "用户只是问『若需重开怎么办』—— 问句不是重开指令",
    ],
    "mechanism": {
        "principle": "append-only，不删不改任何历史字段与证据",
        "requires": "用户显式重开指令（写明触发条件与新的自变量 / 新证据），机器不得自行重开",
        "fieldContract": {
            "status": "closed → open",
            "closed_at": '"2026-11-15" → null',
            "closure": "必须原样保留，不得删除或改写；可在其中追加 reopenedAt 标记",
            "reopen": "新增数组，append-only，每条含 reopened_at / decidedBy / trigger / newIndependentVariable / newCriterion / inheritedCriteria / priorClosurePreserved / evidenceCountBefore / relatedEvidence",
            "appended_evidence": "只追加，不删既有 43 条",
            "updated_at": "改为重开当天日期",
            "title/detail/fix/reader/where/recharacterization": "全部原样保留",
            "known_gaps.topLevel.updated_at": "同步更新；conventions 不动",
        },
        "reportContract": "RESULT 追加新章节（§29 顺延），不改写 §26 / §27 / §28；新章节必须写明重开不是验证通过。",
        "evidenceContract": [
            "新真机回执必须用新前缀（ab6+），不覆盖 ab3 / ab4 / ab5 任何文件",
            "长任务 stdout 全程 tee -a；每轮 start / node-exit / verify 即时写 append-only JSONL；回执由驱动即时落盘",
            "若采用 P2 / P3：改了源码 / dist / Pack 就必须重建 dist、跑全量 npm test + 全量变异 + dist 严格一致性，登记新 hash 基线，并显式标注旧 hash 证据链『断代』",
        ],
    },
    "inheritedCriteria": [
        "只有『A 撞墙且 B 通过』才支持命题；A/B 都通过不能归功边界；A/B 都失败须另找根因",
        "observe-first Gate A：先只跑 A 单轮，判无墙即 ABORT_NO_WALL，不跑 B",
        "B 组硬判据 available===true && messageCountAfter < messageCountBefore",
        "边界未执行或 available:false ⇒ 明写『该轮作废 / 本轮不可评估』，不得包装成『边界无效』",
        "冻结站逐次显式解冻并带 ALLOW_FROZEN=1 留痕，用完仍冻结；预检也算碰冻结站",
        "机器裁定 + 磁盘真证；人工视觉判读单列 nonMachineObservations，不参与机器布尔推导",
    ],
    "costComparison": {
        "keepClosed": "结论保持『命题不可判定』，F1 / F2 / ab4 硬判据 2/2 / ab5 判无墙即停全部不变，零新成本",
        "reopen": "必须付出 P2（回滚 F1，改源码/dist）或 P3（加长会话，改 Pack）的代价；既有 dist hash 与变体 Pack sha256 证据链断代，须重建全部本地门禁并登记新基线；随后才是逐次解冻 + 串行真机 + 按判据裁定",
    },
    "thisTurnAction": {
        "n25StatusChanged": False,
        "statusAfter": n25.get("status"),
        "reopenFieldAdded": False,
        "gitUntouched": True,
        "realMachineRounds": 0,
        "note": "本轮只解释机制并落盘；是否重开须用户显式裁定。",
    },
    "evidence": [
        "RESULT §24 / §26 / §27",
        "wall-observability-diagnosis-2026-11-12.json",
        "proposition-pursuit-plan-2026-11-14.json",
        "ab5-final-verdict-2026-11-14.json",
        "n25-closure-2026-11-15.json",
        "three-items-authorization-closure-verdict-2026-11-15.json",
    ],
}
(EVID / "n25-reopen-mechanism-2026-11-15.json").write_text(
    json.dumps(mechanism, ensure_ascii=False, indent=2) + "\n")

section = """
## §28 ①②③ 授权闭合度与「N25 若需重开」机制（2026-11-15）

### 28.1 开工磁盘真值（跨时段，不认上轮自述）

`three-items-precondition-2026-11-15.json`：`HEAD=36d9ec2`、`origin/main=915c350`、`ahead=0 / behind=33 / unpushed=0 / staged=0`、`status_items=139`（对账脚本落盘前）。台账 25 条 `open 0 / closed 24 / wontfix 1`；N25 `closed` / 43 条证据 / `closed_at=2026-11-15` / `closure.type=INDETERMINABLE_PROPOSITION_CLOSED` / `recharacterization=True`；RESULT 1802 行、§27 共 7 子节；139 份 evidence JSON 全部可解析；`ab6` 目标回执 0。

🔧 **本轮对账自身抓到两处数据缺陷并回溯修正**：
- **D-1（假阳性）**：首个对账脚本对 `git status --porcelain` 整段 stdout 调了 `.strip()`，吃掉首行前导空格，把 `' M chrome-extension/src/background/pack-executor.js'` 误读成 `'M ...'`，报 `staged=1`。复核 `git diff --cached --stat/--raw` 均为空、`ls-files -s` 的 index blob `f151615` 与 HEAD blob 相同、worktree blob `cfc4fa2` 不同 ⇒ **真值 `staged=0`**，是未暂存的 worktree 修改。不得据此 unstage。
- **D-2（真实缺陷）**：同一 `.strip()` 使 `commit-scope-2026-11-14.json` 的 `modifiedTracked.files[0]` 变成 `'hrome-extension/src/background/pack-executor.js'`（首字符 `c` 被切），照该清单逐条 `git add` 会漏 add 或报 pathspec 错。本轮 `commit-scope-2026-11-15.py` 改用 `rstrip('\\n')` 并按前缀断言，已修正为 `chrome-extension/src/background/pack-executor.js`；旧清单作为历史证据保留不覆盖。
- 附带一处开发期即时修正：新盘点脚本首版断言误用子串匹配（`"hrome-extension"` 本就是 `"chrome-extension"` 的子串），改成 `startswith` 后通过。

### 28.2 🔧 回溯补记：`behind=31` 已是过期快照

用户指令写「另需单独授权先处理 behind 31 分歧」。磁盘真值：`origin/main` 由 `19635c6` 被外部 fetch 推进到 `915c350`，新增 2 个提交（`915c350` Merge PR #62、`08ab0f9` 清掉最后 2 处 `continue-on-error`），只改 `.github/workflows/security.yml` 与 `test.yml`；累计 `36d9ec2..origin/main` 共 10 个文件（7 个 workflow + 3 个 adapter-matrix fixture），`ourInputsTouched=[]` —— 未触碰 dist / 变体 Pack / evidence / known_gaps / RESULT / 源码 / 测试。本会话未 fetch / pull / merge / rebase / commit / push。见 `remote-divergence-2026-11-15.2.json`。

**若日后授权 push，须单独授权处理 `behind=33`（不是 31）的分歧。**

### 28.3 ①②③ 逐条授权闭合度（不默认打包）

`three-items-authorization-closure-verdict-2026-11-15.json`：`overall.code = PARTIAL_INTENT_ONLY_NO_EXECUTABLE_AUTHORIZATION`，`executableItemCount = 0`。三条各自独立判定：② 的意图不构成 ③ 的授权；① 前提缺失不构成 ② 的自动放行；任何一条不得靠复述清单升级为授权。

| 条目 | 意图已表达 | 缺口 | 机器裁定 |
|---|---|---|---|
| ① 要跑真机 | 是 | 缺逐次明确解冻 + `ALLOW_FROZEN=1` 留痕；缺「本次改变了哪个自变量」 | `NOT_EXECUTED_PRECONDITION_UNMET` |
| ② 要提交 | 是 | 缺「文件集合」单独授权；旧清单已过期且含 D-2 缺陷 | `COMMIT_ACTION_EXPRESSED_BUT_FILE_SET_NOT_AUTHORIZED` |
| ③ 要 push | 是 | 用户自己写明「另需单独授权」处理分歧，该授权未给 | `NOT_AUTHORIZED_NO_ACTION` |

① 的关键不是「没给解冻」这么简单：§26 已证 A 组 `no-boundary` 本来就是同一会话 8 步串行 / 7 次 AI 往返，自变量结构条件已满足而墙不出现，F1 修复后 3 份完整 A 组回执 8/8、撞墙 0 次。`proposition-pursuit-plan-2026-11-14.json` 五条路径里只有 **P2**（`needsSourceOrDistChange`，回滚 F1 归因对照）和 **P3**（`needsPackChange`，人工加长会话）会改变自变量，代价是改源码/dist 或改 Pack、既有 hash 证据链断代、须重建全部门禁并登记新基线；P1/P4/P5 不改变自变量。首次推导曾按不存在的字段 `changesIndependentVariable` 过滤得到空列表，回读 plan 真实结构后按 `needsPackChange` / `needsSourceOrDistChange` 重算为 P2/P3，已在裁定文件 `derivationCorrection` 留痕。

`commit-scope-2026-11-15.json` 刷新盘点：**145 项 = 15 tracked 改动 + 130 untracked**，`staged=0`，`behind=33`。候选集合：`minimal_this_turn` 6 项、`source_tests_ledger_report` 16 项、`everything` 145 项（用户明令「不要默认一次全收」，仅登记不作默认）。执行方案为 `plan-only / NOT-EXECUTED`，禁止 `git add -A` / `git commit -a` / `--amend` / `--no-verify` / force push / 自动处理分歧。

### 28.4 N25 当前状态的准确含义

N25 是按 `INDETERMINABLE_PROPOSITION_CLOSED` 结案：**结案理由 = 原始观察对象已重新归因、墙不复现、命题不可判定**。不是验证通过（A/B 判据从未成立），不是「边界有效」，也不是「边界无效」，不是「长会话撞墙已根治」。仍成立的事实：F1 等待判据修复真机生效（§21）、F2 `newChat` / `newChatText` 入口真机可达（§23）、ab4 B 组硬判据 2/2 成立、ab5 判无墙即停。原 `title` / `detail` / `fix` / `reader` / `where` / `recharacterization` 与 43 条证据全部原样保留。

### 28.5 什么才构成重开理由（`n25-reopen-mechanism-2026-11-15.json`）

- **T1（唯一能让命题重新可判定的路径）**：出现新的可控自变量，且「墙」可被稳定复现。机器条件：A 组 `stepsTotal==8 && stepSuccess==7`、`firstFailedStepId=='step_8_output'`、错误含 `Response timeout`、前 7 步全成功且 `sessionResets` 为空；人工视觉闸确认不是「服务出错啦，请稍后再试。」且无登录墙 / 验证码；同站相邻时间窗 B 组边界真执行且 `available===true && messageCountAfter<messageCountBefore`。
- **T2**：新证据（可复核磁盘回执）推翻 §24 三条根因 F-D1（等待判据假超时）/ F-D2（站点随机报错）/ F-D3（「长会话是变量」归因被削弱）之一。
- **T3**：找到 §9.4 原始观察里可量化的第三变量（真实上下文 token 长度、站点限流窗口、会话累积时长），且能人为控制并写进新判据。
- **T4**：审计 / 交付口径要求改结论性质，但仍须附新证据。

### 28.6 什么不构成重开理由

想再跑一轮完整 4 轮 A/B（§26 已证盲跑不产生新证据）；台账显示 `closed` 不好看；把 F1 / F2 真机验证挪用为「边界有效」的因果证据；把「边界无效」当结论；仅重述旧证据换措辞；**用户只是问「若需重开怎么办」—— 问句本身不是重开指令**。

### 28.7 重开的技术机制（append-only，不删历史）

须用户显式重开指令，写明触发条件与新的自变量 / 新证据；机器不得自行重开。字段契约：`status: closed → open`、`closed_at: "2026-11-15" → null`、**`closure` 原样保留不删不改**（可追加 `reopenedAt` 标记）、新增 `reopen: []` 数组 append-only（每条含 `reopened_at` / `decidedBy` / `trigger` / `newIndependentVariable` / `newCriterion` / `inheritedCriteria` / `priorClosurePreserved` / `evidenceCountBefore` / `relatedEvidence`）、`appended_evidence` 只追加不删既有 43 条、`updated_at` 改当天、台账顶层 `updated_at` 同步而 `conventions` 不动。RESULT 追加新章节（§29 顺延），不改写 §26 / §27 / §28，且必须写明「重开不是验证通过」。新真机回执用 `ab6+` 新前缀，不覆盖 ab3 / ab4 / ab5。若采用 P2 / P3，改动源码 / dist / Pack 后必须重建 dist、跑全量 `npm test` + 全量变异 + dist 严格一致性，登记新 hash 基线，并显式标注旧 hash 证据链「断代」。

### 28.8 重开后判据继承与成本

判据全部继承：只有「A 撞墙且 B 通过」才支持命题；A/B 都通过不能归功边界，A/B 都失败须另找根因；observe-first Gate A 先只跑 A 单轮、判无墙即 `ABORT_NO_WALL` 不跑 B；B 组硬判据 `available===true && messageCountAfter<messageCountBefore`；边界未执行或 `available:false` ⇒ 明写「该轮作废 / 本轮不可评估」，不得包装成「边界无效」；冻结站逐次显式解冻并带 `ALLOW_FROZEN=1` 留痕、用完仍冻结，预检也算碰冻结站；全程 `tee -a` + 即时 JSONL + 即时回执；机器裁定 + 磁盘真证，人工视觉判读单列 `nonMachineObservations` 不参与布尔推导。

成本对比：**保持 closed** —— 结论就是「命题不可判定」，F1 / F2 / ab4 2/2 / ab5 判无墙即停全部不变，零新成本；**重开** —— 必须付出 P2 或 P3 的改造代价，既有 dist hash 与变体 Pack sha256 证据链断代，重建全部本地门禁并登记新基线后，才是逐次解冻 + 串行真机 + 按判据裁定。

### 28.9 本轮动作与硬边界

本轮 `realMachineRounds=0`：未启动浏览器、未打开冻结站、未发送消息、未产生真机回执；未 commit / push / stage / add / fetch / pull / merge / rebase；未改源码 / 测试 / dist / Pack；**N25 保持 `closed`，未重开、未加 `reopen` 字段**。新增产物全在 `evidence/`：`three-items-precondition-2026-11-15.py/.json`、`remote-divergence-2026-11-15.2.json`、`three-items-authorization-verdict-2026-11-15.py/.json`、`commit-scope-2026-11-15.py/.json`、`n25-reopen-mechanism-2026-11-15.json` 与本节回写脚本。归因边界继续有效：不能把关闭写成验证通过，不能把 F1 / F2 挪用为因果证据，不能把 plan-only 写成已执行回执。
"""

with RESULT.open("a", encoding="utf-8") as f:
    f.write(section)

log_line = """
## 2026-11-15（第 2 段）①②③ 授权闭合度 + N25 重开机制

- 跨时段核磁盘真值：`HEAD=36d9ec2`、`origin/main=915c350`、`behind=33`（用户写 31，过期）、`staged=0`、139→145 项工作区改动；N25 `closed` / 43 证据；RESULT §27 共 7 子节；evidence JSON 全可解析。
- 抓到并回溯修正两处数据缺陷：D-1 本轮对账脚本 `.strip()` 造成 `staged=1` 假阳性（复核 `diff --cached` 空 + index blob == HEAD blob ⇒ 真值 0）；D-2 旧 `commit-scope-2026-11-14.json` 首条路径被切掉 `c`，新盘点用 `rstrip('\\n')` 修正并断言。另修开发期断言子串匹配假阳性。
- `three-items-authorization-closure-verdict-2026-11-15.json`：① `NOT_EXECUTED_PRECONDITION_UNMET`（缺逐次解冻 + 自变量）、② `COMMIT_ACTION_EXPRESSED_BUT_FILE_SET_NOT_AUTHORIZED`、③ `NOT_AUTHORIZED_NO_ACTION`；`executableItemCount=0`，不默认打包。首次推导按不存在字段得空列表，回读 plan 真实字段 `needsPackChange`/`needsSourceOrDistChange` 重算 P2/P3 并留痕。
- `commit-scope-2026-11-15.json`：145 项 = 15 tracked + 130 untracked，候选集合 6 / 16 / 145 项，执行方案 plan-only，禁止 `-A` / `-a` / amend / force push。
- 回答「N25 若需重开」：`n25-reopen-mechanism-2026-11-15.json` + RESULT §28（9 子节）。重开须用户显式指令 + 新可控自变量 / 新证据（T1–T4）；重开机制 append-only：`closed→open`、`closed_at→null`、保留 `closure`、新增 `reopen[]`、证据只追加、RESULT 追加 §29、新回执 ab6+；判据全部继承。本轮不重开。
- 硬边界：未跑真机、未碰冻结站、未提交/推送、未改源码/dist/Pack、N25 保持 closed。
"""
with LOG.open("a", encoding="utf-8") as f:
    f.write(log_line)

print(json.dumps({
    "n25Status": n25.get("status"),
    "resultLinesAfter": len(RESULT.read_text().splitlines()),
    "section28Subsections": section.count("\n### 28."),
    "reopenMechanismJson": (EVID / "n25-reopen-mechanism-2026-11-15.json").stat().st_size,
    "logExists": LOG.exists(),
}, ensure_ascii=False, indent=2))
