# RESULT — N29 qianwen 会话重置回归修复（2026-11-18）

- **状态**: completed（N29 根因确认并修复；活跃 5 站修复后全部复验通过）
- 日期：2026-11-18
- 执行者：`claude_code`（AGENT_EXEC）
- 工作区：`/private/tmp/wt-g11`（`origin/main @ 44e4114`）
- 范围：只改新会话入口选择逻辑；未解冻 deepseek / longcat，未改 A/B 判据

> **口径声明**：本轮所有真机回执的 `platformPolicy` 均为
> `{allowed:true, active:true, unfrozenBy:null, reason:"active"}`。
> 未使用 `ALLOW_FROZEN=1`，未打开任何冻结站。

## 1 · 根因：不是「点不动」，是「点错了元素」

### 证据 A —— 页面结构在 11-11 → 11-18 之间变了

只读探针 `new-session-probe.mjs` 的两份磁盘证据：

| 时间 | 文件 | hover-reveal 外层祖先 | 外层 `newChatReveal-*` 的 rendered |
|---|---|---|---|
| 11-11 | `new-session-probe-2026-11-11.chatglm-kimi-qianwen-yiyan-yuanbao.json` | `… pointer-events-none opacity-0` | false |
| 11-18 | `new-session-probe-2026-11-18.qianwen-n29.json` | `… flex min-h-0 min-w-0 flex-col ` | **true** |

11-18 的真入口 `outerHTML`：

```html
<div class="newChatReveal-OikAdB newChatRevealFlat-hnO8At">
  <div class="flex h-full gap-0.5">
    <div data-session-switch-target="new-chat" class="… cursor-pointer">
      <span class="truncate font-400">新对话</span>
    </div>
  </div>
</div>
```

### 证据 B —— 生产选择器顺序会先命中外层容器

`findNewSessionControl()` 原顺序是 adapter → 可见文案 → 隐藏语义。
可见文案层扫 `[class*="newChat"]`，而外层 `div.newChatReveal-*` 同时满足：

- 类名含 `newChat`；
- `textContent` 全等于「新对话」；
- 11-18 起 `isElementRendered === true`。

11-11 它不可见所以被跳过，隐藏语义层命中真入口（12→0）；
11-18 它可见，于是**先被返回并点击**——但外层容器没有 click handler。

用今天的 DOM 形状在 jsdom 里跑生产函数，逐字复现真机回执：

```
found.how = text-match
found.el  = <div class="newChatReveal-OikAdB newChatRevealFlat-hnO8At">…
found 是语义控件? null
handleNewSession = {"available":false,"strategy":"click-no-effect",
  "reason":"点了「新对话」但消息数没有下降（6 → 6），无法确认会话已重置。",
  "messageCountBefore":6,"messageCountAfter":6,"durationMs":910}
```

### 证据 C —— 真入口本身是好的

在持久化 profile 上打开一条历史会话（7 条消息），只对
`[data-session-switch-target="new-chat"]` 调 `.click()`，不发送任何消息：

```
before-click  total=7   url=/chat/34fde9f2…
after 1000ms  total=0   url=/chat
clicks: [{targetAttr:"new-chat", …}]
```

证据：`N29-qianwen-click-diagnostic.json` / `.png`。

⇒ 结论：站点把 hover 面板改成默认可见后，**宽泛文案层抢在窄语义层前面**，
点了一个同名但没有处理器的容器。不是 site 拒绝程序化点击，也不是代码 commit 回归
（`new-session-control.js` 自 11-11 未改）。

## 2 · 修复

`chrome-extension/src/content/new-session-control.js`：

1. 在 adapter 层与可见文案层之间插入**可见语义属性层**：
   只扫 `HIDDEN_SEMANTIC_SELECTORS`，必须通过 `isElementRendered`，命中返回
   `how: "semantic"`。
2. 抽出共用判据 `semanticControlMatches()`：文案全等 / aria-label 全等 /
   带 `new_chat` 的锚点，并排除 composer 区诱饵。
3. 隐藏兜底层**仍留在最后**，复用同一判据。安全边界不变：
   不会因为新层而提前点击不可见元素，也没有放宽 `span` / `div` 标签（
   那会误点 longcat 历史列表里的「新对话」诱饵）。

没有改 adapter 的 `newChat` 表——千问入口会在可见 / hover 隐藏之间切换，
写死选择器只会把故障从「容器抢答」换成「隐藏时命中不了」。

## 3 · 验证

### 单元与变异

```
node --test tests/new-session-control.test.mjs      → 11 passed, 0 failed
CODEBUDDY_SAFE_DELETE_ENABLED=0 npm test            → 326 passed, 0 failed
变异检查                                            → 125/125 全部被杀死
  ✓ 可见语义层被清空（千问 2026-11-18 的 newChatReveal 容器抢答回归）
      被「千问 2026-11-18：hover-reveal 面板默认可见时…」杀死
```

新增守护用例同时覆盖 11-11 隐藏态（仍 `hidden-semantic`）与 11-18 可见态
（新层 `semantic`，消息 6→0）。

### 真机：修复后活跃 5 站全部通过

| 平台 | success | steps | 会话重置 | 策略 | 消息数 | unfrozenBy |
|---|---|---|---|---|---|---|
| qianwen | true | 8/8 | true | **semantic** | 6→0 | null |
| yuanbao | true | 8/8 | true | adapter-selector | 12→0 | null |
| chatglm | true | 8/8 | true | adapter-selector | 12→0 | null |
| yiyan | true | 8/8 | true | adapter-selector | 6→0 | null |
| kimi | true | 8/8 | true | adapter-selector | 6→0 | null |

qianwen 首轮重跑（`L2-qianwen-auto-2026-11-18.n29fix.full8.json`）在 step_6
撞站点 `Response timeout`，没跑到 step_8，`sessionResets` 为空；如实留档，
不算通过。第二轮 `.n29fix2` 8/8 完成，`durationMs=308`，策略 `semantic`。

kimi 仍用 `/tmp/rm-l2-profile-copy-20261118` 副本规避本机 safe-delete 阈值，
没有绕过守卫去删 `~/Library` 下的 Chrome 缓存。

## 4 · 结论与边界

- **N29 可以关闭**：根因有探针、jsdom 复现、点击诊断、真机前后对照四层证据；
  修复后 qianwen 从 6→6 变成 6→0。
- **用户设的前置条件已满足**：活跃 5 站 Pack 层 5/5、会话重置层 5/5，
  冻结闸门零触碰。
- **本轮仍然不启动解冻**：冻结站登录态未核、32 步额度未确认，且解冻需要用户
  对 `ALLOW_FROZEN=1` 的明确授权。这里只把「全部验证跑通」这个前置事实交付。
- 不改 N25 的 A/B 判据；将来 B 组仍须 `available === true && after < before`。

## acceptance_commands

```bash
# 1 · 单元
cd chrome-extension && node --test tests/new-session-control.test.mjs

# 2 · 全套
cd chrome-extension && CODEBUDDY_SAFE_DELETE_ENABLED=0 npm test

# 3 · 变异（新增那条必须被指定用例杀死）
cd chrome-extension && CODEBUDDY_SAFE_DELETE_ENABLED=0 node tests/real-machine/mutation-check.mjs 2>&1 | grep -A1 '可见语义层被清空'

# 4 · 五站回执统一对账（只读）
python3 - <<'PY'
import json, pathlib
base = pathlib.Path('collaboration/results/real-machine-runs/evidence')
for p in ['qianwen','yuanbao','chatglm','yiyan','kimi']:
    suffix = 'n29fix2' if p == 'qianwen' else 'n29fix'
    d = json.loads((base / f'L2-{p}-auto-2026-11-18.{suffix}.full8.json').read_text())
    e, r = d['exec'], d['exec']['result']
    sr = r['sessionResets'][0]
    print(p, e['success'], len(r['steps']), sr['available'], sr['strategy'],
          sr['messageCountBefore'], sr['messageCountAfter'],
          d['platformPolicy']['unfrozenBy'])
PY

# 5 · 冻结闸门：所有回执 unfrozenBy 必须为 null
#     见上面第 4 条最后一列

# 6 · OpenSpec
openspec validate fix-qianwen-visible-semantic-control --strict
```
