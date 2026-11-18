#!/usr/bin/env python3
"""2026-11-12 后续步骤③：deepseek 精确文案逃生口本地修复的机器裁定。

只读以下磁盘证据，机械推导布尔值，不手写结论：
  - gates-deepseek-newchat-2026-11-12.summary.json
  - dist-consistency-2026-11-12.deepseek-newchat.json
  - npm-test-2026-11-12.deepseek-newchat.log
  - mutation-check-2026-11-12.deepseek-newchat.full.log
  - 源码两处关键声明（只读，不 import、不执行）

真机未跑就是未跑：realMachineVerified 恒由「本轮是否产出了新站点回执」决定，
本地门禁全绿不得把它推成 true。N25 只能在 A/B 判据成立后关闭。
"""
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
OUT = HERE / "deepseek-newchat-verdict-2026-11-12.json"


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"__error__": str(exc)}


def read(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return f"__ERROR__ {exc}"


summary = load(HERE / "gates-deepseek-newchat-2026-11-12.summary.json")
dist = load(HERE / "dist-consistency-2026-11-12.deepseek-newchat.json")
test_log = read(HERE / "npm-test-2026-11-12.deepseek-newchat.log")
mutation_log = read(HERE / "mutation-check-2026-11-12.deepseek-newchat.full.log")

# ── 单测：从 TAP 汇总行机械解析 ──────────────────────────────────
def tap_count(key, text):
    m = re.search(rf"^# {key}\s+(\d+)\s*$", text, re.M)
    return int(m.group(1)) if m else None


tests_total = tap_count("tests", test_log)
tests_pass = tap_count("pass", test_log)
tests_fail = tap_count("fail", test_log)
tests_ok = (
    tests_total is not None
    and tests_pass == tests_total
    and tests_fail == 0
    and tests_total > 0
)

# ── 变异：必须「全部 N 条被杀死」且 N 与退出码一致 ────────────────
m_mut = re.search(r"全部\s+(\d+)\s+条变异都被杀死。", mutation_log)
mutation_total = int(m_mut.group(1)) if m_mut else None
mutation_killed = mutation_log.count("\n✓ ")
mutation_ok = (
    mutation_total is not None
    and mutation_total > 0
    and "变异存活" not in mutation_log
    and mutation_killed == mutation_total
)
mutation_exit = summary.get("mutationFull")

# ── dist：核产物本身 ──────────────────────────────────────────────
dist_all_pass = dist.get("allPass") is True
idempotent = dist.get("idempotent") is True
keyword_checks = dist.get("keywordChecks", [])
keywords_ok = bool(keyword_checks) and all(k.get("pass") is True for k in keyword_checks)

# ── 源码：逃生口是否真的落地（只读字符串核对，不执行）──────────────
adapter_src = read(REPO / "chrome-extension/src/platforms/deepseek-adapter.js")
control_src = read(REPO / "chrome-extension/src/content/new-session-control.js")
newchat_text_declared = "newChatText:" in adapter_src and 'texts: ["开启新对话"]' in adapter_src
exact_text_layer = "adapter-text-match" in control_src and "const textRule = config?.newChatText;" in control_src
public_span_not_widened = '"span",' not in control_src.split("NEW_SESSION_CONTROL_SELECTOR")[1].split("].join")[0]

# ── 真机：本轮有没有新站点回执？──────────────────────────────────
# 本轮门禁脚本不启动浏览器、不导入 Pack、不发送。用「本轮产物里是否存在
# 新 L2 回执」做机械判据：只认以 deepseek-newchat 命名的新回执文件。
new_receipts = sorted(HERE.glob("*deepseek-newchat*L2-*.json"))
real_machine_verified = len(new_receipts) > 0

# ── git ──────────────────────────────────────────────────────────
try:
    head = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, text=True).strip()
    origin = subprocess.check_output(["git", "rev-parse", "--short", "origin/main"], cwd=REPO, text=True).strip()
    status_items = len(subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO, text=True).splitlines())
except Exception as exc:  # noqa: BLE001
    head = origin = f"ERROR: {exc}"
    status_items = None

all_gates_pass = bool(
    summary.get("allPass") is True
    and summary.get("build1") == 0
    and summary.get("build2") == 0
    and summary.get("idempotent") is True
    and summary.get("npmTest") == 0
    and mutation_exit == 0
    and summary.get("distConsistency") == 0
    and summary.get("distAllPass") is True
    and tests_ok
    and mutation_ok
    and dist_all_pass
    and idempotent
    and keywords_ok
    and newchat_text_declared
    and exact_text_layer
    and public_span_not_widened
)

local_fix_complete = bool(newchat_text_declared and exact_text_layer and public_span_not_widened)
proposition_supported = False  # A/B 判据「A 撞墙且 B 通过」从未成立
n25_status = "open"

if all_gates_pass and not real_machine_verified:
    code = "LOCAL_FIX_GATES_PASS_REAL_MACHINE_NOT_VERIFIED"
elif all_gates_pass and real_machine_verified:
    code = "LOCAL_FIX_GATES_PASS_REAL_MACHINE_RECEIPT_FOUND_REVIEW_REQUIRED"
else:
    code = "GATES_FAILED_OR_INCOMPLETE"

verdict = {
    "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "mode": "deepseek-newchat-local-fix-verdict",
    "scope": "2026-11-12 后续步骤①–③：deepseek adapter 级精确文案逃生口 + 全量本地门禁",
    "code": code,
    "localFixComplete": local_fix_complete,
    "allGatesPass": all_gates_pass,
    "realMachineVerified": real_machine_verified,
    "propositionSupported": proposition_supported,
    "n25": {
        "status": n25_status,
        "decision": "remain open",
        "reason": "只有 A/B 跑完且「A 撞墙且 B 通过」判据成立才允许关闭；本轮没有真机 A/B 回执。",
    },
    "evidence": {
        "gatesSummary": "gates-deepseek-newchat-2026-11-12.summary.json",
        "gatesLog": "gates-deepseek-newchat-2026-11-12.log",
        "gatesProgress": "gates-deepseek-newchat-2026-11-12.jsonl",
        "npmTestLog": "npm-test-2026-11-12.deepseek-newchat.log",
        "mutationLog": "mutation-check-2026-11-12.deepseek-newchat.full.log",
        "distConsistency": "dist-consistency-2026-11-12.deepseek-newchat.json",
        "buildLogs": [
            "build-2026-11-12.deepseek-newchat.log",
            "build-2026-11-12.deepseek-newchat-second.log",
        ],
    },
    "gates": {
        "build1": summary.get("build1"),
        "build2": summary.get("build2"),
        "idempotent": idempotent,
        "npmTest": summary.get("npmTest"),
        "npmTestTotals": {"total": tests_total, "pass": tests_pass, "fail": tests_fail, "ok": tests_ok},
        "mutationFull": mutation_exit,
        "mutationTotals": {"declaredKilled": mutation_total, "tickLines": mutation_killed, "ok": mutation_ok},
        "distConsistency": summary.get("distConsistency"),
        "distAllPass": dist_all_pass,
        "keywordChecks": {"total": len(keyword_checks), "allPass": keywords_ok},
    },
    "sourceChecks": {
        "newChatTextDeclaredInDeepseekAdapter": newchat_text_declared,
        "exactTextLayerPresent": exact_text_layer,
        "publicSelectorNotWidenedToSpan": public_span_not_widened,
    },
    "git": {"head": head, "originMain": origin, "statusItems": status_items, "committed": False, "pushed": False},
    "newRealMachineReceipts": [p.name for p in new_receipts],
    "attributionBoundaries": [
        "全绿只证明本地门禁；不能说 deepseek 的会话边界在真机上生效。",
        "不能说会话边界解掉 step_8 撞墙，也不能说边界无效。",
        "不能把 F1 公共等待判据的真机成功挪用为 fresh_session 的因果证据。",
        "不能说重置免费，不能把耗时差异归因给重置。",
        "本轮未打开冻结站、未导入 Pack、未发送任何消息、未 commit / push。",
    ],
    "nextRequiresAuthorization": [
        "明确解冻 deepseek / longcat 并授权真机重跑（逐次 ALLOW_FROZEN=1 留痕）。",
        "预检核登录态 → 相邻时间窗串行跑 4 轮 A/B（B 组须 available===true && messageCountAfter<Before）。",
        "按判据裁定 N25；此前保持 open。",
        "提交 / push 需单独授权，且按提交与文件集合分清。",
    ],
}

OUT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"written": str(OUT), "code": code, "allGatesPass": all_gates_pass,
                  "realMachineVerified": real_machine_verified, "n25": n25_status}, ensure_ascii=False))
