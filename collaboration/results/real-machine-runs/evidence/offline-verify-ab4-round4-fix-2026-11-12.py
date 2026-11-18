#!/usr/bin/env python3
"""离线重放验证 ab4 第 4 轮补跑脚本的两处 bug 修复。

§23.3 记录了两个脚本自身 bug：
  B1 前置检查把 Path.replace()（文件系统重命名）误当字符串 replace；
  B2 收尾 verify 把退出码字符串也转成 Path，int(ec) 抛 TypeError。
两处都已在 ab4-round4-rerun-2026-11-12.sh 里修好，但修好后**没有再跑过真机**
（不该为验证脚本 bug 重复发送）。本脚本用纯离线方式验证修复有效：
  - 静态断言：修后代码在、旧错误代码不在、两段 Python 的 stderr 都接进 tee；
  - bash -n 语法检查；
  - 用 tempfile + 已有 4 份回执重放两处逻辑，确认不再抛错、结果正确。
硬红线：不启动浏览器、不打开冻结站、不写真机 OUT、不覆盖任何既有证据、
        不调用 l2-platform-auto.mjs、不碰 git。
"""
import json
import pathlib
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[3]
SCRIPT = HERE / "ab4-round4-rerun-2026-11-12.sh"
RUNNER = HERE / "ab4-runner-2026-11-12.sh"
OUT = HERE / "offline-verify-ab4-round4-fix-2026-11-12.json"

checks = []
def check(name, ok, detail):
    checks.append({"name": name, "pass": bool(ok), "detail": detail})

src = SCRIPT.read_text(encoding="utf-8")
runner_src = RUNNER.read_text(encoding="utf-8")

check("B1 修后代码存在（out_name.name.replace）",
      'out_name.name.replace(".json", suffix)' in src,
      "用 str 做后缀替换，不再触发 Path.replace 的文件重命名")
check("B1 旧错误代码已消失",
      'ev / out_name.replace(".json", suffix)' not in src,
      "防止回归")
check("B2 修后代码存在（ec 保持字符串）",
      "ec = _args[4]" in src and "int(ec)" in src,
      "只有前 4 个参数转 Path，退出码仍是字符串")
check("B2 旧错误代码已消失",
      "out, a_receipt, prog, summary, ec = [pathlib.Path(x) for x in sys.argv[1:6]]" not in src,
      "防止回归")
check("两段 Python 的 stderr 都接进 tee",
      src.count("2>&1 | tee -a") >= 2,
      "避免再次出现『崩溃了但日志里什么都没有』")
check("日志 append-only、不覆盖失败证据",
      "ROUND4_ATTEMPT_BOUNDARY" in src and ': > "$RUNLOG"' not in src,
      "第一次 PRECONDITION_FAILED 保留在盘")

for name, path in [("补跑脚本", SCRIPT), ("ab4 runner", RUNNER)]:
    r = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
    check(f"bash -n {name}", r.returncode == 0, r.stderr.strip() or "语法 OK")

# ── 离线重放 B1：目标路径推导 ──────────────────────────────────
with tempfile.TemporaryDirectory() as td:
    ev = pathlib.Path(td)
    out_name = pathlib.Path("L2-longcat-auto-2026-11-12.ab4-with-boundary.json")
    derived = []
    try:
        for suffix in [".json", ".png"]:
            derived.append((ev / out_name.name.replace(".json", suffix)).name)
        b1_ok = derived == [
            "L2-longcat-auto-2026-11-12.ab4-with-boundary.json",
            "L2-longcat-auto-2026-11-12.ab4-with-boundary.png",
        ]
        b1_err = ""
    except Exception as exc:
        b1_ok, b1_err = False, repr(exc)
    check("B1 离线重放：后缀替换结果正确且无异常", b1_ok, b1_err or str(derived))

    # ── 离线重放 B2：收尾 verify 的参数拆解 ────────────────────
    receipt = HERE / "L2-longcat-auto-2026-11-12.ab4-with-boundary.json"
    a_receipt = HERE / "L2-longcat-auto-2026-11-12.ab4-no-boundary.json"
    prog = ev / "progress.jsonl"
    summary = ev / "summary.json"
    args = [str(receipt), str(a_receipt), str(prog), str(summary), "0"]
    try:
        _a = args[:5]
        o, a, p, s = [pathlib.Path(x) for x in _a[:4]]
        ec = _a[4]
        node_exit = int(ec)
        d = json.loads(o.read_text(encoding="utf-8"))
        r = (d.get("exec") or {}).get("result") or {}
        steps = r.get("steps") or []
        resets = r.get("sessionResets") or []
        f = resets[0] if resets else None
        before = f.get("messageCountBefore") if isinstance(f, dict) else None
        after = f.get("messageCountAfter") if isinstance(f, dict) else None
        available = f.get("available") if isinstance(f, dict) else None
        reset_ok = bool(available is True and isinstance(before, int)
                        and isinstance(after, int) and after < before)
        replay = {
            "nodeExit": node_exit,
            "stepsTotal": len(steps),
            "stepSuccess": sum(1 for x in steps if x.get("success") is True),
            "status": r.get("status"),
            "sessionResets": len(resets),
            "resetActuallyHappened": reset_ok,
            "resetBefore": before, "resetAfter": after,
        }
        b2_ok = (node_exit == 0 and replay["stepsTotal"] == 8
                 and replay["stepSuccess"] == 7 and replay["resetActuallyHappened"] is True
                 and replay["resetBefore"] == 6 and replay["resetAfter"] == 0)
        b2_err = ""
    except Exception as exc:
        b2_ok, b2_err, replay = False, repr(exc), {}
    check("B2 离线重放：int(ec) 不再抛错，回执解析结果正确", b2_ok,
          b2_err or json.dumps(replay, ensure_ascii=False))

all_pass = all(c["pass"] for c in checks)
result = {
    "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "mode": "offline-replay-verify-ab4-round4-script-fixes",
    "status": "offline-only / NOT-EXECUTED-ON-REAL-MACHINE",
    "scope": "2026-11-12 后续步骤①的本地准备：验证 §23.3 两处脚本 bug 已修",
    "allPass": all_pass,
    "checks": checks,
    "hardBoundaries": {
        "browserLaunched": False,
        "frozenSitesOpened": False,
        "messagesSent": False,
        "realMachineOutWritten": False,
        "existingEvidenceOverwritten": False,
        "l2PlatformAutoInvoked": False,
        "gitTouched": False,
    },
    "note": "离线验证通过只证明脚本不再因自身 bug 假失败，不代表任何新的真机结论；N25 保持 open。",
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"written": str(OUT), "allPass": all_pass,
                  "checks": len(checks), "failed": [c["name"] for c in checks if not c["pass"]]},
                 ensure_ascii=False, indent=2))
sys.exit(0 if all_pass else 1)
