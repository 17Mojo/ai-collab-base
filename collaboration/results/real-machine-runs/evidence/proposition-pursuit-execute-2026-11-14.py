#!/usr/bin/env python3
"""按 2026-11-14 用户裁定执行 P1：收口改述 N25（不关闭）+ 逐维授权结果落盘。

硬边界：不改 status/closed_at、不覆盖 N25 原有字段、不改 Pack/源码/测试/dist、
不启动浏览器、不发消息、不碰 git（不 commit/push/stage/fetch/pull/merge/rebase）。
"""
import json
import pathlib
import datetime
import subprocess

REPO = pathlib.Path("/Users/raymondna/Documents/AI-collab/ai-collab-base")
EV = REPO / "collaboration/results/real-machine-runs/evidence"
RESULT = REPO / "collaboration/results/RESULT-L2-MULTIPLATFORM-2026-11-10.md"
GAPS = REPO / "known_gaps.json"
WORKLOG = pathlib.Path("/Users/raymondna/WorkBuddy/2026-11-04-12-09-59/.workbuddy/memory/2026-11-14.md")
RULING = EV / "proposition-pursuit-ruling-2026-11-14.json"
OUT_REPORT = EV / "proposition-pursuit-execution-2026-11-14.json"

def git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()

def truth():
    return {
        "head": git("rev-parse", "--short", "HEAD"),
        "originMain": git("rev-parse", "--short", "origin/main"),
        "ahead": int(git("rev-list", "--count", "origin/main..HEAD") or 0),
        "behind": int(git("rev-list", "--count", "HEAD..origin/main") or 0),
        "unpushed": int(git("rev-list", "--count", "origin/main..HEAD") or 0),
        "staged": len([x for x in git("diff", "--cached", "--name-only").splitlines() if x.strip()]),
        "statusItems": len([x for x in git("status", "--porcelain").splitlines() if x.strip()]),
    }

plan = json.loads((EV / "proposition-pursuit-plan-2026-11-14.json").read_text())
final_ab5 = json.loads((EV / "ab5-final-verdict-2026-11-14.json").read_text())

# ── 1. 裁定证据 ─────────────────────────────────────────────
ruling = {
    "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "mode": "proposition-pursuit-and-reauthorization-ruling",
    "userMandate": "处理后续步骤：1、追究命题；2、重新授权（2026-11-14）",
    "answers": [
        {"id": "q-0", "header": "追究路径", "answer": "P1 收口改述 N25（推荐）"},
        {"id": "q-1", "header": "解冻真机", "answer": "不解冻（推荐）"},
        {"id": "q-2", "header": "提交动作", "answer": "暂不提交（推荐）"},
        {"id": "q-3", "header": "文件集合", "answer": "仅本轮产物（推荐）"},
    ],
    "effective": {
        "p1RecharacterizeN25": True,
        "closeN25": False,
        "unfreezeDeepseekLongcat": False,
        "commit": False, "push": False, "stage": False,
        "resolveRemoteDivergence": False,
        "realMachineRounds": 0,
    },
    "scopeClarification": {
        "reauthorizationObject": "用户只说『重新授权』，宾语未指明；已拆成 6 个独立维度分别确认，未默认打包",
        "q3IsPreferenceOnly": True,
        "q3Note": "q-2 裁定『暂不提交』，因此 q-3『仅本轮产物』仍是 PREFERENCE_ONLY_NOT_AUTHORIZATION，不是本次提交授权，也不是一次全收 127+ 项",
        "dimensions": {
            "A1_追究路径": "P1（已裁定并执行）",
            "A2_逐次解冻": "未授权（用完仍是冻结，白名单代码未改）",
            "A3_git_commit": "未授权",
            "A4_文件集合": "仅偏好登记，未授权",
            "A5_behind4分歧处理": "未授权（behind=4 保持不动）",
            "A6_push": "未授权",
        },
    },
    "sourceEvidence": {
        "plan": plan["mode"] + " / " + plan["status"],
        "diagnosis": "wall-observability-diagnosis-2026-11-12.json",
        "ab5": final_ab5["code"],
        "resultSection": "§26",
    },
    "noRealMachineAction": True,
    "gitUntouched": True,
    "diskTruthAtRuling": truth(),
}
RULING.write_text(json.dumps(ruling, ensure_ascii=False, indent=2) + "\n")

# ── 2. N25 改述（保留原字段，不关闭）────────────────────────
gaps = json.loads(GAPS.read_text())
n25 = next(x for x in gaps["gaps"] if str(x.get("id")) == "N25")
assert n25["status"] == "open", "P1 不授权关闭；若 status 已变须停机复核"
assert n25["closed_at"] is None, "closed_at 必须仍为 null"
assert "recharacterization" not in n25, "改述字段已存在，拒绝覆盖历史"

rechar = {
    "at": "2026-11-14",
    "decidedBy": "用户 2026-11-14 裁定 P1（AskUserQuestion q-0）",
    "originalNature": "待 A/B 验证：deepseek / longcat 冻结中不可验，需解冻跑 A/B 才能判定『会话边界解掉了 step_8 长会话撞墙』",
    "revisedNature": "已跑 A/B，但原始观察对象已重新归因、命题不可判定",
    "reader": (
        "想把 N25 写成『边界解掉长会话撞墙』或『边界无效』的人；以及想再申请解冻盲跑 4 轮的人——"
        "F1 后 3 份 A 组结构复现（同一会话 8 步串行 / 7 次 AI 往返）全部 8/8、撞墙 0 次，"
        "ab5 observe-first 又是 ABORT_NO_WALL，继续跑真机不产生新的成对因果证据。"
    ),
    "basis": [
        "wall-observability-diagnosis-2026-11-12.json: F-D1 deepseek 假超时已由 F1 根治；F-D2 longcat 站点随机报错是外部混杂变量；F-D3 隔离实验不足以支持『长会话是变量』",
        "proposition-pursuit-plan-2026-11-14.json: 机械汇总 8 份 A 组回执，F1 后走满 8 步的 3 份全部 8/8 completed，step_8 13333/12310/11736 ms，sessionResets=0，撞墙 0 次",
        "ab5-final-verdict-2026-11-14.json: ABORT_NO_WALL，roundsExecuted=1，B 与 longcat 均未跑，propositionSupported=false",
    ],
    "statusKeptOpen": (
        "用户明令 N25 只能在 A/B 跑完且判据成立之后关闭；判据从未成立。"
        "本次 P1 只授权性质改述，未授权关闭，故 status=open / closed_at=null 保持不动。"
    ),
    "isNot": [
        "不是说边界无效", "不是说命题不成立（不成立需可判定的对照轮次）",
        "不是说 F1 / F2 真机验证无效", "不是说长会话从未被复现（结构条件已满足，墙不出现）",
        "不是说 N25 已关闭",
    ],
    "originalFieldsPreserved": True,
    "note": "本字段只做性质改述留痕；原 title / detail / fix / reader / where 一律不删不改，便于接手者考古原始口径。",
}
n25["recharacterization"] = rechar
before = len(n25["appended_evidence"])
n25["appended_evidence"].append(
    "2026-11-14 用户裁定 P1『收口改述 N25』并逐维确认重新授权范围（evidence/proposition-pursuit-ruling-2026-11-14.json）："
    "q-0=P1 收口改述、q-1=不解冻、q-2=暂不提交、q-3=仅本轮产物（因 q-2 为暂不提交，仍属 PREFERENCE_ONLY_NOT_AUTHORIZATION，不是本次授权）。"
    "N25 新增 recharacterization 字段，性质由『待 A/B 验证』改述为『已跑 A/B，但原始观察对象已重新归因、命题不可判定』；"
    "原 title/detail/fix/reader/where 全部保留不覆盖；status 仍 open、closed_at 仍 null、优先级不动，关闭仍需单独裁定。"
    "六维授权：A1 路径已裁定 P1；A2 逐次解冻未授权（用完仍冻结、白名单代码未改）；A3 commit 未授权；A4 文件集合仅偏好登记未授权；"
    "A5 behind=4 分歧处理未授权；A6 push 未授权。本轮 realMachineRounds=0、未启动浏览器/未打冻结站/未发消息/未改 Pack/源码/测试/dist/未碰 git。"
    "回写 RESULT §26.7–26.8、本日志。注意：origin/main 仍 f98a1a7、本地 HEAD 36d9ec2、behind 4，若日后授权 push 须先单独授权处理分歧。"
)
n25["status"] = "open"
n25["closed_at"] = None
n25["updated_at"] = "2026-11-14"
gaps["updated_at"] = "2026-11-14"
GAPS.write_text(json.dumps(gaps, ensure_ascii=False, indent=2) + "\n")

# ── 3. RESULT §26.7 / §26.8 ─────────────────────────────────
section = """

### 26.7 用户裁定与 P1 执行（`proposition-pursuit-ruling-2026-11-14.json`）

四个维度分别确认，未默认打包：

| 问题 | 裁定 | 效力 |
|---|---|---|
| q-0 追究路径 | **P1 收口改述 N25** | 已执行，见下 |
| q-1 解冻真机 | **不解冻** | 不启动浏览器、不打开冻结站、不跑预检、不发消息；用完仍是冻结，白名单代码未改 |
| q-2 提交动作 | **暂不提交** | 不 commit / push / stage / merge / rebase；127+ 项全留工作区 |
| q-3 文件集合 | **仅本轮产物** | 因 q-2 为暂不提交，仍是 `PREFERENCE_ONLY_NOT_AUTHORIZATION`，**不是**本次提交授权，也不是一次全收 |

P1 的具体落地：N25 新增 `recharacterization` 结构化字段，性质由「待 A/B 验证」改述为「**已跑 A/B，但原始观察对象已重新归因、命题不可判定**」；写明 `reader`、三条机器证据依据、`isNot` 四条边界、以及「关闭仍需单独裁定」。`status` 保持 `open`、`closed_at` 保持 `null`、优先级不动；**原 `title` / `detail` / `fix` / `reader` / `where` 全部保留不覆盖**，符合台账 `conventions` 的「关闭后保留条目」与「每条必须写 reader」精神，也便于接手者考古原始口径。N25 证据 41→42。

六维授权结果：A1 路径已裁定 P1；**A2 解冻 / A3 commit / A4 文件集合 / A5 behind=4 分歧处理 / A6 push 全部保持未授权**。`behind=4` 分歧不动。

### 26.8 最终磁盘真证与状态

本轮 `realMachineRounds=0`，硬边界全 false：未启动浏览器、未打开冻结站、未发送消息、未改 Pack、未改源码 / 测试 / dist、未碰 git、未产生真机回执。新增产物全部在 `evidence/` 下：`proposition-pursuit-plan-2026-11-14.py/.json`、`proposition-writeback-2026-11-14.py`、`proposition-pursuit-ruling-2026-11-14.json`、`proposition-pursuit-execution-2026-11-14.json`。

归因边界继续有效：不能说边界有效、也不能说边界无效；不能把 F1 / F2 真机验证挪用为因果证据；不能说「长会话撞墙已根治」（准确说法是**原始观察已重新归因、结构条件复现但墙不出现**）；站点侧报错须单独标注；不能把 `plan-only` 写成已执行回执。

后续步骤（均未授权，按依赖顺序）：① 若要关闭 N25，须单独明确裁定；② 若要跑真机，须逐次明确解冻并说明本次改变了哪个自变量（否则 §26 已证盲跑不产生新证据）；③ 若要提交，须按「提交动作」与「文件集合」分别重新授权；④ 若 push，还须单独授权先处理 `behind=4` 分歧。
"""
with RESULT.open("a") as f:
    f.write(section)

with WORKLOG.open("a") as f:
    f.write("\n- **裁定与执行（P1）**：用户 q-0=P1 收口改述 N25、q-1=不解冻、q-2=暂不提交、q-3=仅本轮产物（因暂不提交，仍是 PREFERENCE_ONLY_NOT_AUTHORIZATION）。N25 新增 `recharacterization` 字段：性质由「待 A/B 验证」改述为「已跑 A/B，但原始观察对象已重新归因、命题不可判定」，带 reader/三条机器证据/isNot/关闭仍需单独裁定；status 仍 open、closed_at 仍 null、原 title/detail/fix/reader/where 全部保留不覆盖。六维授权除 A1 外全部保持未授权，behind=4 不动，realMachineRounds=0，未碰 git。回写 RESULT §26.7–26.8、N25 证据 41→42、本日志。\n")

# ── 4. 执行汇总证据 ─────────────────────────────────────────
txt = RESULT.read_text()
fs = sorted(EV.glob("*.json"))
bad = []
for p in fs:
    try:
        json.loads(p.read_text())
    except Exception as e:
        bad.append(p.name)
exec_doc = {
    "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "mode": "proposition-pursuit-p1-execution-readonly-verification",
    "status": "EXECUTED_LOCAL_ONLY",
    "realMachineRounds": 0,
    "diskTruth": {
        "head": truth()["head"], "originMain": truth()["originMain"],
        "ahead": truth()["ahead"], "behind": truth()["behind"],
        "unpushed": truth()["unpushed"], "staged": truth()["staged"],
        "statusItems": truth()["statusItems"],
        "resultLines": len(txt.splitlines()),
        "resultSection26Subsections": sum(1 for l in txt.splitlines() if l.startswith("### 26.")),
        "knownGapsCount": len(gaps["gaps"]),
        "n25Status": n25["status"], "n25ClosedAt": n25["closed_at"],
        "n25EvidenceCount": len(n25["appended_evidence"]),
        "n25Recharacterized": "recharacterization" in n25,
        "n25OriginalFieldsPreserved": all(k in n25 for k in ("title", "detail", "fix", "reader", "where")),
        "evidenceJsonTotal": len(fs), "evidenceJsonParseFailures": len(bad),
    },
    "authorizationState": ruling["scopeClarification"]["dimensions"],
    "hardBoundaries": {
        "noRealMachineAction": True, "noBrowserLaunch": True, "noMessageSent": True,
        "noPackChange": True, "noSourceOrDistChange": True, "noGitChange": True,
        "noReceiptCreated": True,
    },
    "note": "只核磁盘真值，不是 L2 回执、不证明命题成立与否。",
}
OUT_REPORT.write_text(json.dumps(exec_doc, ensure_ascii=False, indent=2) + "\n")

print("WROTE", RULING.name, "/", OUT_REPORT.name)
print("N25 evidence", before, "->", len(n25["appended_evidence"]))
print("N25 status =", n25["status"], "closed_at =", n25["closed_at"], "recharacterized =", "recharacterization" in n25)
print("RESULT lines =", len(txt.splitlines()), "§26 subsections =", exec_doc["diskTruth"]["resultSection26Subsections"])
print("evidence json =", len(fs), "parse failures =", len(bad))
print("git =", json.dumps(truth(), ensure_ascii=False))
