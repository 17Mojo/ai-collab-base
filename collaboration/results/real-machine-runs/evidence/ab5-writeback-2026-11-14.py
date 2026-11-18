#!/usr/bin/env python3
"""ab5 回写：RESULT §25 / known_gaps.json N25 appended_evidence / 工作日志。

只做文本与台账追加，不改源码、不碰 git、不产生真机回执。
"""
import json
import pathlib
import datetime

REPO = pathlib.Path("/Users/raymondna/Documents/AI-collab/ai-collab-base")
EV = REPO / "collaboration/results/real-machine-runs/evidence"
RESULT = REPO / "collaboration/results/RESULT-L2-MULTIPLATFORM-2026-11-10.md"
GAPS = REPO / "known_gaps.json"
WORKLOG = pathlib.Path("/Users/raymondna/WorkBuddy/2026-11-04-12-09-59/.workbuddy/memory/2026-11-14.md")

FINAL = json.loads((EV / "ab5-final-verdict-2026-11-14.json").read_text())
GATE_A = json.loads((EV / "ab5-gate-a-verdict-2026-11-14.json").read_text())

# ── 1. RESULT §25 ────────────────────────────────────────────
section = """

---

## §25 执行「后续步骤」：解冻 + observe-first 单轮 → ABORT_NO_WALL，N25 保持 open（2026-11-14）

用户 2026-11-14 明令：「解冻并按 observe-first gate 重跑（先跑 A 单轮，判无墙即停），而不是盲跑 4 轮；逐次 `ALLOW_FROZEN=1` 留痕。Gate A 判「墙不存在」→ `ABORT_NO_WALL`，N25 仍 open；仅当 Gate A 成立才跑 B 并按判据裁定。提交 / push 按「提交」与「文件集合」分别确认，不要默认一次全收。」时间跨了 2 天，先核磁盘真值，不认上轮自述。

### 25.1 跨 2 天只读前置对账（`ab5-precondition-2026-11-14.json`，`preconditionPass=true`）

| 项 | 磁盘真值 | 结论 |
|---|---|---|
| HEAD / origin/main | `36d9ec2` / `36d9ec2`，`unpushed=0` | 一致 |
| 工作区 | 105 项（落盘本证据时 106） | 与 `commit-scope-2026-11-12.json` 分类一致 |
| dist | `content-script.js 5b4807bd…` / `service-worker.js fe3122cb…` | 与 `dist-consistency-2026-11-12.deepseek-newchat.json` 逐文件 hash 一致，幂等构建证据 `allPass=true` |
| 变体 Pack | `89b197cf…` / `0e1b4b98…` | 与 ab5 plan 声明一致，**未改 Pack** |
| `L2-*.ab5-*.json/.png` 目标路径 | 0 个占用 | 不覆盖任何既有证据 |
| SW 缓存 | Service Worker 8 / Extension Scripts 5 / Code Cache 缺失 = 13 项 | 远低于 shim 的 50 阈值，无需绕过安全门 |
| ab5 plan 状态 | `plan-only / NOT-EXECUTED`、`noRealMachineAction=true` | 未被偷跑 |

授权留痕：用户明令全文写进 `authorization.verbatim`；`unfrozenPlatforms=[deepseek,longcat]`；`perCommandFlag=ALLOW_FROZEN=1`；`appliesToPrecheck=true`；`whitelistCodeChanged=false`；`usageRule=逐次显式放行，用完仍是冻结`。**代码白名单未改**。

### 25.2 判据留白不暗猜：Gate A 首轮平台由用户裁定

ab5 plan 的 `gateA.description` 只写「先只跑 A 组（no-boundary）单轮」，**未钉死 platform**。前置证据把该项标为 `openCriterion.resolution=PENDING_USER_CONFIRMATION`，并向用户出具只读探测得到的两条依据：deepseek 在 F1 修复后 ab3/ab4 两轮 A 全 8/8、`step_8` 12.3–13.6s，原始「答案迟到 4×180s」已重新归因为虚拟列表假超时；longcat 失败步在 `step_3/4/6/8` 漂移、截图同型「服务出错啦」站点报错，属外部混杂变量。

用户 `AskUserQuestion q-0` 裁定 **deepseek**。裁定独立落盘 `ab5-gate-a-platform-ruling-2026-11-14.json`（`roundsTotal=1`，`onGateAFalse=ABORT_NO_WALL`），**不覆盖**前置证据里的 PENDING 历史留痕。

### 25.3 显式解冻预检（`L2-precheck-2026-11-14.ab5.deepseek-longcat.json`）

`CANDIDATES=deepseek,longcat PRECHECK=1 ALLOW_FROZEN=1`，全程 `tee -a ab5-precheck-2026-11-14.log`。两站 `composerVisible=true` / `looksLikeLogin=false`；`platformPolicy` 两站均 `allowed=true / active=false / unfrozenBy=ALLOW_FROZEN=1 / reason=frozen-but-explicitly-unfrozen`。SW 缓存仅清 2 项，**未设置** `CODEBUDDY_SAFE_DELETE_ENABLED=0`。

### 25.4 observe-first：只跑 1 轮 A（`ab5-observe-first-runner-2026-11-14.sh`）

`PRECONDITION_OK` 后仅执行 `deepseek / no-boundary` 一轮，`NODE_EXIT=0`，耗时 1m19s。落盘口径全部满足：stdout 全程 `tee -a ab5-observe-first-2026-11-14.log`；`start / node-exit / verify / verify written / runner done` 即时写 append-only `ab5-observe-first-progress-2026-11-14.jsonl`；回执由驱动自身即时写 OUT；结尾 `RECEIPT_PRESENT=True`。

| 字段 | A 单轮真值 |
|---|---|
| 回执 | `L2-deepseek-auto-2026-11-14.ab5-no-boundary.json`（17968 B） |
| `exec.success` / `status` | `true` / `completed` |
| steps | **8/8 全成功**，`duration=74558ms` |
| `step_8_output` | **成功，11736ms** |
| `sessionResets` | **0**（A 组无边界，符合变体） |
| `platformPolicy.unfrozenBy` | `ALLOW_FROZEN=1` |
| 首失败步 | **无**（`firstFailedStepId=null`） |

截图 `L2-deepseek-auto-2026-11-14.ab5-no-boundary.png` 已落盘。

### 25.5 Gate A 机器裁定（`ab5-gate-a-verdict-2026-11-14.json`）

`ab5-gate-a-verdict-2026-11-14.py` 只读回执，机械判 6 条判据：

| 判据 | 结果 |
|---|---|
| C1 `stepsTotal==8` | ✅ |
| C2 `stepSuccess==7` | ❌（实际 8） |
| C3 `firstFailedStepId=='step_8_output'` | ❌（无失败步） |
| C4 错误含 `Response timeout` | ❌（无失败步） |
| C5 前 7 步全成功 | ✅ |
| C6 A 组 `sessionResets` 为空 | ✅ |

`machinePass=false` ⇒ **`code=ABORT_NO_WALL`**，`bShouldRun=false`。按判据**不跑 B、不跑 longcat**。

### 25.6 人工视觉巡检（`nonMachineObservation`，不参与机器布尔）

`ViewImage` 判读截图：末条 AI 回复是**正常中文长文本**（AI 智能体定义与场景说明），不是「服务出错啦，请稍后再试。」；无登录墙、无验证码/滑块。左栏「开启新对话」入口可见，但本轮是 `no-boundary`、**未触发任何 `NEW_SESSION`**，不得据此说 F2 在本轮真机生效。该观察在 `ab5-final-verdict-2026-11-14.json` 里单列 `visualObservation.participatesInMachineBoolean=false`，**不改变 `ABORT_NO_WALL` 结论**。

### 25.7 ABORT 分支硬核与归因边界（`ab5-final-verdict-2026-11-14.json`）

只读核磁盘：`bReceipt / longcatAReceipt / longcatBReceipt` 三个 ab5 目标路径 **全部 `exists=false`**；`roundsExecuted=1`、`bActuallyRun=false`、`longcatActuallyRun=false`；`progressEvents` 只有单轮的 6 条事件。

- 只有「A 撞墙且 B 通过」才支持命题；本轮 A 未撞墙、B 未跑 ⇒ **`propositionSupported=false`**，`boundaryIneffectiveClaimed=false`。
- **不能说边界有效，也不能说边界无效**；不能把「A 8/8 通过」归功边界；不能把既往 F1 / F2 真机验证挪用为 A/B 因果证据。
- `f1RealMachineVerifiedThisRound=false` / `f2RealMachineVerifiedThisRound=false`：本轮 `sessionResets=0`，没有触发会话边界，不新增任何 F1/F2 因果结论；§21 / §23 的既往结论不翻案。
- 准确说法是：**本轮墙不存在，判无墙即停**；§24 的「原始观察已重新归因、墙不复现」得到又一次同型真机佐证，但这不是「长会话撞墙已被根治」的因果证明。
- **N25 保持 `open`**，`closed_at=null`。

### 25.8 产物与状态

新增：`ab5-precondition-2026-11-14.py/.json`、`ab5-gate-a-platform-ruling-2026-11-14.json`、`L2-precheck-2026-11-14.ab5.deepseek-longcat.json`、`ab5-precheck-2026-11-14.log`、`ab5-observe-first-runner-2026-11-14.sh`、`ab5-observe-first-2026-11-14.log`、`ab5-observe-first-progress-2026-11-14.jsonl`、`ab5-observe-first-verify-2026-11-14.json`、`L2-deepseek-auto-2026-11-14.ab5-no-boundary.json/.png`、`ab5-gate-a-verdict-2026-11-14.py/.json`、`ab5-final-verdict-2026-11-14.py/.json`。

本轮**未改源码 / 未重建 dist / 未改变体 Pack / 未改冻结白名单 / 未跑 B / 未跑 longcat / 未 `git commit` / 未 `git push`**。提交 / push 按「提交」与「文件集合」分别确认，不默认一次全收。

### 25.9 后续步骤（均未授权，按依赖顺序）

1. 若仍要追究命题：先解决 §24 的自变量不可控问题（原始墙已重新归因），再申请**新的逐次解冻**；不得直接盲跑 4 轮。
2. 提交 / push 单独授权：按「是否提交」与「提交哪个文件集合」两个问题分别确认，`commit-scope-2026-11-12.json` 已有分类清单。
"""

with RESULT.open("a") as f:
    f.write(section)
print("RESULT appended §25, new lines =", section.count("\n"))

# ── 2. known_gaps.json N25 ───────────────────────────────────
gaps = json.loads(GAPS.read_text())
items = gaps["gaps"] if isinstance(gaps, dict) else gaps
n25 = next(x for x in items if str(x.get("id")) == "N25")
before = len(n25["appended_evidence"])
n25["appended_evidence"].extend([
    "2026-11-14 跨 2 天只读前置对账 evidence/ab5-precondition-2026-11-14.json（preconditionPass=true、errors=[]）：HEAD/origin 均 36d9ec2、unpushed=0、status_items=105（落盘本证据后 106）；dist content-script.js 5b4807bd…/service-worker.js fe3122cb… 与 dist-consistency-2026-11-12.deepseek-newchat.json 逐文件 hash 一致且幂等；两个变体 Pack 89b197cf…/0e1b4b98… 与 ab5 plan 声明一致、未改 Pack；L2-*.ab5-* 目标 .json/.png/.dom-samples.json 全部为空；SW 缓存 13 项远低于 shim 50 阈值；ab5 plan 仍为 plan-only/NOT-EXECUTED、noRealMachineAction=true，未被偷跑。授权留痕：用户 2026-11-14 明令全文写入 authorization.verbatim，unfrozenPlatforms=[deepseek,longcat]、perCommandFlag=ALLOW_FROZEN=1、appliesToPrecheck=true、whitelistCodeChanged=false、usageRule=逐次放行用完仍冻结；提交/push 未授权。前置证据显式标注 openCriterion「Gate A 首轮平台」resolution=PENDING_USER_CONFIRMATION（plan 未钉死 platform，不暗猜）。",
    "2026-11-14 判据裁定与预检：用户 AskUserQuestion q-0 裁定 Gate A 首轮平台 = deepseek，独立落盘 evidence/ab5-gate-a-platform-ruling-2026-11-14.json（roundsTotal=1、onGateAFalse=ABORT_NO_WALL、onGateATrue 才跑同站 B 且视觉闸须人确认；不覆盖前置证据的 PENDING 历史留痕）。依据：F1 后 deepseek ab3/ab4 两轮 A 全 8/8、step_8 12.3–13.6s，原始『答案迟到 4×180s』已重新归因为虚拟列表假超时；longcat 失败步漂移且截图同型站点报错属外部混杂变量。显式解冻预检 CANDIDATES=deepseek,longcat PRECHECK=1 ALLOW_FROZEN=1 → evidence/L2-precheck-2026-11-14.ab5.deepseek-longcat.json：两站 composerVisible=true/looksLikeLogin=false，platformPolicy 两站均 allowed=true/active=false/unfrozenBy=ALLOW_FROZEN=1；SW 缓存仅清 2 项，未设 CODEBUDDY_SAFE_DELETE_ENABLED=0。",
    "2026-11-14 observe-first 真机单轮：evidence/ab5-observe-first-runner-2026-11-14.sh 前置 PRECONDITION_OK 后只跑 1 轮 A（deepseek/no-boundary），NODE_EXIT=0，耗时 1m19s。回执 L2-deepseek-auto-2026-11-14.ab5-no-boundary.json（17968B）：exec.success=true、status=completed、8/8 步全成功、duration=74558ms、step_8_output 成功 11736ms、sessionResets=0、firstFailedStepId=null、platformPolicy.unfrozenBy=ALLOW_FROZEN=1。落盘口径：stdout 全程 tee -a ab5-observe-first-2026-11-14.log；start/node-exit/verify/verify written/runner done 即时写 append-only ab5-observe-first-progress-2026-11-14.jsonl；回执由驱动自身即时写 OUT；结尾 RECEIPT_PRESENT=True。截图 L2-deepseek-auto-2026-11-14.ab5-no-boundary.png 落盘。未跑 B、未跑 longcat、未盲跑 4 轮。",
    "2026-11-14 机器裁定与停机：evidence/ab5-gate-a-verdict-2026-11-14.py/.json 只读回执机械判 6 条 Gate A 判据 ⇒ C1✅/C2❌(实际 8≠7)/C3❌(无失败步)/C4❌(无 Response timeout)/C5✅/C6✅，machinePass=false ⇒ code=ABORT_NO_WALL、bShouldRun=false。人工视觉巡检（nonMachineObservation，participatesInMachineBoolean=false）：截图末条 AI 回复是正常中文长文本，非『服务出错啦，请稍后再试。』，无登录墙/验证码/滑块；左栏『开启新对话』可见但本轮 no-boundary 未触发任何 NEW_SESSION，不得据此说 F2 本轮真机生效。evidence/ab5-final-verdict-2026-11-14.py/.json 硬核磁盘：bReceipt/longcatAReceipt/longcatBReceipt 三个 ab5 目标路径全 exists=false，roundsExecuted=1、bActuallyRun=false、longcatActuallyRun=false、progressEvents 仅单轮 6 条。结论 propositionSupported=false、boundaryIneffectiveClaimed=false、f1RealMachineVerifiedThisRound=false、f2RealMachineVerifiedThisRound=false；不能说边界有效也不能说边界无效、不能把 A 8/8 归功边界、不能挪用既往 F1/F2 真机验证为因果证据；准确说法是『本轮墙不存在，判无墙即停』，§24 的『原始观察已重新归因、墙不复现』得到又一次同型真机佐证但不是因果证明。N25 保持 open、closed_at=null。回写 RESULT §25（9 子节）、本日志；本轮未改源码/未重建 dist/未改 Pack/未改冻结白名单/未 git commit/未 git push。",
])
n25["status"] = "open"
n25["closed_at"] = None
n25["updated_at"] = "2026-11-14"
GAPS.write_text(json.dumps(gaps, ensure_ascii=False, indent=2) + "\n")
print("N25 evidence", before, "->", len(n25["appended_evidence"]),
      "| status", n25["status"], "| closed_at", n25["closed_at"])

# ── 3. 工作日志（append-only）───────────────────────────────
WORKLOG.parent.mkdir(parents=True, exist_ok=True)
log = """
## 2026-11-14 ab5 observe-first：解冻 + 单轮 A → ABORT_NO_WALL

- 用户明令「解冻并按 observe-first gate 重跑（先跑 A 单轮，判无墙即停），而不是盲跑 4 轮；Gate A 判墙不存在→ABORT_NO_WALL、N25 仍 open；提交/push 按提交与文件集合分别确认、不要默认一次全收」。跨 2 天先核磁盘真值，不认上轮自述。
- 前置对账 `ab5-precondition-2026-11-14.json` preconditionPass=true：HEAD/origin 36d9ec2、unpushed=0、105 项；dist 与 Pack hash 全部一致；`*.ab5-*` 目标路径全空；SW 缓存 13 项；ab5 plan 仍 NOT-EXECUTED。授权留痕写入用户明令全文、逐次 ALLOW_FROZEN=1、白名单代码未改、用完仍冻结。
- **不暗猜判据**：plan 的 Gate A 未钉死首轮平台，前置证据标 PENDING_USER_CONFIRMATION；用户 AskUserQuestion q-0 裁定 deepseek，独立落盘 `ab5-gate-a-platform-ruling-2026-11-14.json`（单轮，不覆盖 PENDING 历史）。
- 预检 `CANDIDATES=deepseek,longcat PRECHECK=1 ALLOW_FROZEN=1`：两站 composerVisible=true / looksLikeLogin=false，platformPolicy.unfrozenBy=ALLOW_FROZEN=1、active=false。
- 真机只跑 1 轮 A（deepseek/no-boundary），`ab5-observe-first-runner-2026-11-14.sh` NODE_EXIT=0、1m19s：8/8 completed、74558ms、step_8 成功 11736ms、sessionResets=0、无失败步。全程 tee + 即时 JSONL + 即时回执 + RECEIPT_PRESENT。
- Gate A 机器裁定 `ab5-gate-a-verdict-2026-11-14.json`：C2/C3/C4 不成立 ⇒ **ABORT_NO_WALL**，不跑 B、不跑 longcat。人工视觉巡检单列 nonMachineObservation（末条 AI 回复是正常长文本、非站点报错、无登录墙；左栏新对话入口可见但未触发 NEW_SESSION），不参与机器布尔。
- 最终裁定 `ab5-final-verdict-2026-11-14.json`：硬核 B/longcat 三个 ab5 回执全不存在；roundsExecuted=1、propositionSupported=false、boundaryIneffectiveClaimed=false；不能说边界有效也不能说无效，不能挪用既往 F1/F2 为因果证据；N25 保持 open、closed_at=null。
- 回写 RESULT §25（9 子节）、known_gaps.json N25 证据 36→40。本轮未改源码/未重建 dist/未改 Pack/未改冻结白名单/未 commit/未 push。
- 口径沉淀：observe-first 判无墙即停，比盲跑 4 轮省 3/4 额度；判据留白必须先裁定再动真机，不能靠猜。
"""
with WORKLOG.open("a") as f:
    f.write(log)
print("WORKLOG appended", WORKLOG.name)
