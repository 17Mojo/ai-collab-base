# Implementation Tasks

> 凡勾选者必须附**实测证据（命令 + 关键输出）**，不写「已完成」了事。
> 证据按编号 E1–E6 引用，集中列在文末。

## Phase 0 · 立项与隔离

- [x] 0.1 从 `origin/main @ 44e4114` 开独立分支；主工作区在途改动零影响（E1）
- [x] 0.2 产出 `proposal.md` / `specs/new-session-boundary/spec.md` 增量 / `tasks.md`（E1）
- [x] 0.3 `openspec validate fix-qianwen-visible-semantic-control --strict` 零错误（E1）

## Phase 1 · 根因取证

- [x] 1.1 只读探针对比 11-11 / 11-18 的 hover-reveal 可见性变化（E2）
- [x] 1.2 用今天的 DOM 形状在 jsdom 里逐字复现 `click-no-effect 6→6`（E2）
- [x] 1.3 在持久化 profile 上直接点真语义入口，确认 7→0、真入口没坏（E3）

## Phase 2 · 代码

- [x] 2.1 插入「可见语义属性层」，返回 `how: "semantic"`，位于文案层之前（E4）
- [x] 2.2 抽 `semanticControlMatches()`，可见层与隐藏兜底层共用判据（E4）
- [x] 2.3 隐藏兜底仍留最后；不改 adapter 表、文案表、A/B 判据（E4）

## Phase 3 · 验证

- [x] 3.1 新增 jsdom 可见态回归用例；11-11 隐藏态用例仍绿（E5）
- [x] 3.2 扩展全套 326 条测试全绿（E5）
- [x] 3.3 变异检查 125/125 被杀死，新增那条被指定用例杀死（E5）
- [x] 3.4 用修复后的 dist 重跑活跃 5 站完整 L2，5/5 Pack + 5/5 会话重置（E6）

## Phase 4 · 收口

- [x] 4.1 `known_gaps.json` N29 → closed，附四层证据（E7）
- [x] 4.2 提交带 pathspec、PR、合入登记、归档、`validate --archived --strict`（E8）

## 实测证据

### E1 · 隔离与工件

```
分支: fix/qianwen-visible-semantic-control-2026-11-18
基线: origin/main @ 44e4114
主工作区在途改动: 全程未碰

$ openspec validate fix-qianwen-visible-semantic-control --strict
Change 'fix-qianwen-visible-semantic-control' is valid
```

### E2 · DOM 变化与 jsdom 复现

```
11-11 探针: 外层祖先含 pointer-events-none opacity-0，newChatReveal rendered=false
11-18 探针: 外层祖先无这两个类，newChatReveal rendered=true，opacity=1
  evidence/new-session-probe-2026-11-18.qianwen-n29.json

jsdom（今天 DOM 形状 + 生产函数）:
found.how = text-match
found 是语义控件? null
handleNewSession = {"available":false,"strategy":"click-no-effect",
  "messageCountBefore":6,"messageCountAfter":6,"durationMs":910}
```

### E3 · 真入口没坏

```
evidence/N29-qianwen-click-diagnostic.json
opened-history: url=/chat/34fde9f2… total=7
before-click:   total=7
after 1000ms:   total=0  url=/chat
clicks: [{targetAttr:"new-chat", …}]
```

### E4 · 代码落点

```
src/content/new-session-control.js
  + semanticControlMatches(el, wanted)
  + 可见语义层：for (sel of HIDDEN_SEMANTIC_SELECTORS) { if (!isElementRendered(el)) continue; … how:"semantic" }
  ~ 隐藏兜底层改为复用同一判据
  ~ JSDoc 返回类型加 "semantic"
未改: qianwen-adapter.js / NEW_SESSION_TEXTS / NEW_SESSION_CONTROL_SELECTOR / A-B 判据
```

### E5 · 单测、全套与变异

```
node --test tests/new-session-control.test.mjs   → 11 passed, 0 failed
CODEBUDDY_SAFE_DELETE_ENABLED=0 npm test          → 326 passed, 0 failed
变异检查                                          → 125/125 全部被杀死
  ✓ 可见语义层被清空（千问 2026-11-18 的 newChatReveal 容器抢答回归）
      被「千问 2026-11-18：hover-reveal 面板默认可见时…」杀死
```

### E6 · 修复后真机（活跃 5 站）

```
qianwen  True completed 8/8  True  semantic          6→0  unfrozenBy=null  (.n29fix2)
yuanbao  True completed 8/8  True  adapter-selector 12→0  unfrozenBy=null
chatglm  True completed 8/8  True  adapter-selector 12→0  unfrozenBy=null
yiyan    True completed 8/8  True  adapter-selector  6→0  unfrozenBy=null
kimi     True completed 8/8  True  adapter-selector  6→0  unfrozenBy=null
ALL PASS: True

首轮 qianwen .n29fix 在 step_6 撞站点 Response timeout，未跑到 step_8；
回执与截图如实留档，不算通过。第二轮 .n29fix2 才计入。
kimi 使用 /tmp profile 副本规避本机 safe-delete 阈值，未绕过守卫。
```

结论报告：`collaboration/results/RESULT-N29-QIANWEN-SEMANTIC-CONTROL-2026-11-18.md`。

### E7 · 台账关单

```
$ python3 -c "import json; from collections import Counter; d=json.load(open('known_gaps.json')); print(len(d['gaps']), Counter(g['status'] for g in d['gaps']))"
29 Counter({'closed': 27, 'wontfix': 1, 'open': 1})

N29: status=closed, closed_at=2026-11-18
唯一仍 open 的条目: N25（冻结站 A/B，需用户明确授权，本 change 不触碰）
```

### E8 · 合入留痕

```
PR #78: https://github.com/17Mojo/ai-collab-base/pull/78
合入提交（40 位完整 sha）: 718dde192f5df3cafc063ccaef3816903c3074d6
CI: chrome-extension-tests pass；Bandit / python-tests ×3 为 PR #72–#77 既有红灯，
    本 change 未新增 CI 错误。
```
