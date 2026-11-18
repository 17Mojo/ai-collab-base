#!/usr/bin/env python3
"""2026-11-14 补记：收口时 origin/main 已被外部推进 4 个提交。

回溯修正 §25.1 的开工快照，不删原文，只加时点说明；同时把这个事实写进
commit-scope 清单与工作日志。只读 + 追加，不碰 git、不产生回执。
"""
import json
import pathlib
import datetime
import subprocess

REPO = pathlib.Path("/Users/raymondna/Documents/AI-collab/ai-collab-base")
EV = REPO / "collaboration/results/real-machine-runs/evidence"
RESULT = REPO / "collaboration/results/RESULT-L2-MULTIPLATFORM-2026-11-10.md"
SCOPE = EV / "commit-scope-2026-11-14.json"
WORKLOG = pathlib.Path("/Users/raymondna/WorkBuddy/2026-11-04-12-09-59/.workbuddy/memory/2026-11-14.md")
HANDOFF = EV / "remote-divergence-2026-11-14.json"

def git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()

head = git("rev-parse", "--short", "HEAD")
origin = git("rev-parse", "--short", "origin/main")
behind = int(git("rev-list", "--count", "HEAD..origin/main") or 0)
ahead = int(git("rev-list", "--count", "origin/main..HEAD") or 0)
commits = [x for x in git("log", "--oneline", "36d9ec2..origin/main").splitlines() if x.strip()]
files = [x for x in git("diff", "--name-only", "36d9ec2..origin/main").splitlines() if x.strip()]
touched_ours = [f for f in files if any(k in f for k in (
    "chrome-extension/dist", "ab-pack", "real-machine-runs/evidence", "known_gaps", "RESULT"))]

rec = {
    "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "mode": "remote-divergence-readonly",
    "observedAt": "2026-11-14 最终收口对账",
    "openingSnapshot": {"head": "36d9ec2", "originMain": "36d9ec2", "at": "2026-11-14T07:34Z"},
    "closingSnapshot": {"head": head, "originMain": origin, "behind": behind, "ahead": ahead},
    "newRemoteCommits": commits,
    "changedFiles": files,
    "source": "git reflog origin/main 两次 fetch --quiet origin: fast-forward（外部推进，非本会话操作）",
    "ourInputsTouched": touched_ours,
    "impactOnAb5": "none：未触碰 dist / 变体 Pack / evidence / known_gaps / RESULT；ab5 前置 hash 复核、Gate A 裁定、ABORT_NO_WALL 结论全部保持有效",
    "correction": "§25.1 表格里的『HEAD/origin 均 36d9ec2』是开工时（07:34Z）磁盘真值，不是收口时真值；收口时本地 behind=4、ahead=0，未推送提交数仍为 0。原文保留留痕，本条为回溯补记。",
    "localAction": "本会话未执行 fetch / pull / merge / rebase / commit / push；本地 HEAD 未移动",
    "implicationForCommit": "若后续授权提交：本地落后远端 4 个提交，push 前需先处理分歧（合并/rebase），该动作须单独授权，不得默认执行",
    "gitUntouched": True,
}
HANDOFF.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n")

# 把分歧事实并入 commit-scope 清单
scope = json.loads(SCOPE.read_text())
scope["remoteDivergence"] = {
    "head": head, "originMain": origin, "behind": behind, "ahead": ahead,
    "unpushed": 0, "newRemoteCommits": commits, "changedFiles": files,
    "ourInputsTouched": touched_ours,
    "note": "开工快照 originMain=36d9ec2；收口时已由外部 fetch 前进到 " + origin +
            "。本会话未 fetch/pull/merge/rebase/commit/push。若授权提交，push 前须单独授权处理 behind=4。",
    "evidence": HANDOFF.name,
}
scope["note"] = scope["note"] + " 注意：本地落后远端 4 个提交，见 remoteDivergence。"
SCOPE.write_text(json.dumps(scope, ensure_ascii=False, indent=2) + "\n")

section = """

### 25.10 收口时补记：`origin/main` 已被外部推进 4 个提交（回溯修正 §25.1）

最终磁盘真证对账发现，§25.1 表格里的「HEAD / origin/main 均 `36d9ec2`」是**开工时（07:34Z）**快照；收口时 `origin/main = f98a1a7`，本地 `HEAD = 36d9ec2`，**behind 4 / ahead 0 / unpushed 0**。`git reflog show origin/main` 显示两次 `fetch --quiet origin: fast-forward`，来自外部推进，**不是本会话操作**；本会话未执行 fetch / pull / merge / rebase / commit / push，本地 HEAD 未移动。

| 新远端提交 | 说明 |
|---|---|
| `9dc4da9` | `ci(nightly): 给 pytest 管道显式开 pipefail，别让 tee 吞掉失败` |
| `b577d05` | `test(adapter-matrix): 同步 kimi/longcat/yiyan 快照到 11-11 真机选择器` |
| `3173dd7` | Merge PR #47 |
| `f98a1a7` | Merge PR #48 |

改动文件只有 `.github/workflows/nightly.yml` 与 3 个 `chrome-extension/tests/adapter-matrix/fixtures/mock-dom-*.html`，**未触碰 dist / 变体 Pack / evidence / known_gaps / RESULT**。因此 §25.1 的 hash 复核、§25.4 单轮回执、§25.5 Gate A 裁定、§25.7 `ABORT_NO_WALL` 结论全部保持有效，不需要翻案。原文不删，留痕。

对提交的现实影响：若后续授权提交并推送，本地落后远端 4 个提交，**push 前必须先处理分歧（merge / rebase）**，该动作须单独授权，不得默认执行。见 `remote-divergence-2026-11-14.json` 与 `commit-scope-2026-11-14.json` 的 `remoteDivergence` 字段。
"""
with RESULT.open("a") as f:
    f.write(section)

with WORKLOG.open("a") as f:
    f.write("\n- **收口补记**：`origin/main` 被外部 fetch 推进到 `f98a1a7`（PR #47/#48 共 4 提交），本地 HEAD 仍 `36d9ec2`、behind 4 / ahead 0 / unpushed 0。新提交只改 nightly.yml 与 3 个 adapter-matrix fixture，未触碰 ab5 任何输入 ⇒ 结论不翻案。本会话未 fetch/pull/merge/rebase/commit/push。若后续授权提交，push 前须单独授权处理落后 4 个提交的分歧。回写 RESULT §25.10、`remote-divergence-2026-11-14.json`、commit-scope 清单的 remoteDivergence 字段。\n")

print("WROTE", HANDOFF.name)
print("closing:", head, origin, "behind", behind, "ahead", ahead)
print("commits:", len(commits), "files:", len(files), "ourInputsTouched:", touched_ours)
print("RESULT §25.10 appended; scope + worklog updated")
