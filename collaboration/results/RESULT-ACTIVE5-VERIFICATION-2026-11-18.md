# RESULT — 活跃 5 站完整验证（2026-11-18）

- **状态**: completed（Pack 层全通；会话重置层 4/5，**不宣称全绿**）
- 日期：2026-11-18
- 执行者：`claude_code`（AGENT_EXEC）
- 工作区：`/private/tmp/wt-g11`（`origin/main @ 44e4114`）
- 范围：按用户指令「用那 5 个活跃站完成全部验证，解冻放在全部验证跑通后再处理」

> **口径声明**：本轮**只碰白名单 5 站**（qianwen / yuanbao / chatglm / yiyan / kimi），
> 未使用 `ALLOW_FROZEN=1`，未打开 deepseek / longcat。5 份回执的 `platformPolicy`
> 均为 `{allowed:true, active:true, unfrozenBy:null, reason:"active"}`——可从磁盘复核。
>
> **Pack 通过 ≠ 会话重置通过**。本轮 5/5 Pack 8/8 完成，但 qianwen 的 `step_8`
> 会话重置失败。两者必须分开说。

## 执行命令

环境准备（当前代码，不是旧产物）：

```
cd /private/tmp/wt-g11/chrome-extension
ln -s /Users/raymondna/Documents/AI-collab/ai-collab-base/chrome-extension/node_modules node_modules
npm run build                                   # 当前 origin/main 的 dist
```

登录态预检（只开页面、不发包）：

```
PRECHECK=1 OUT=.../L2-precheck-2026-11-18.active5.json \
  node tests/real-machine/l2-platform-auto.mjs
```

完整 L2（每站 8 步 Pack，串行）：

```
PLATFORM=<p> OUT=.../L2-<p>-auto-2026-11-18.full8.json \
  node tests/real-machine/l2-platform-auto.mjs
# <p> ∈ {qianwen, yuanbao, chatglm, yiyan, kimi}
# kimi 因本机安全守卫改用 PROFILE=/tmp/rm-l2-profile-copy-20261118（原 profile 的副本）
```

## 验证结果

### 1 · Pack 层：5/5 全通

| 平台 | success | status | 步骤 | 截图 |
|---|---|---|---|---|
| qianwen | true | completed | 8/8 | `L2-qianwen-auto-2026-11-18.full8.png` |
| yuanbao | true | completed | 8/8 | `L2-yuanbao-auto-2026-11-18.full8.png` |
| chatglm | true | completed | 8/8 | `L2-chatglm-auto-2026-11-18.full8.png` |
| yiyan | true | completed | 8/8 | `L2-yiyan-auto-2026-11-18.full8.png` |
| kimi | true | completed | 8/8 | `L2-kimi-auto-2026-11-18.full8.png` |

回执均在 `collaboration/results/real-machine-runs/evidence/L2-*-auto-2026-11-18.full8.json`。
预检 5/5：`composerVisible: true`、`looksLikeLogin: false`，登录态有效。

### 2 · 会话重置层：4/5，qianwen 回归

| 平台 | available | strategy | 消息数 |
|---|---|---|---|
| chatglm | true | adapter-selector | 12→0 |
| kimi | true | adapter-selector | 6→0 |
| yiyan | true | adapter-selector | 6→0 |
| yuanbao | true | adapter-selector | 12→0 |
| **qianwen** | **false** | **click-no-effect** | **6→6** |

qianwen 回执原文：

```
sessionResets[0] = {
  available: false,
  strategy: "click-no-effect",
  reason: "点了「新对话」但消息数没有下降（6 → 6），无法确认会话已重置。",
  messageCountBefore: 6,
  messageCountAfter: 6,
  durationMs: 8232
}
```

`new-session-control.js:277-297` 在 `waitForSessionReset` 超时后主动 `refuse` 为
`click-no-effect`——这是**诚实的失败判定**，不是代码吞错。

对照 2026-11-11 同站：`L2-qianwen-auto-2026-11-11.n23.json` 为
`available=true / hidden-semantic / 12→0`；同日另有一次
`available=false / none / 12→12`。`git log` 显示 `new-session-control.js`
自 11-11 起未改（唯一提交 `2297186` 在 N23 期间）。因此这是**页面 DOM 或会话状态变化**
导致的回落，不是代码 commit 回归——但目前没有足够磁盘证据判定是哪一种。

已登记为 **N29（P1 / open）**。

### 3 · kimi 的本机安全守卫插曲（不是站点问题）

首轮 kimi 在 `clearSwCaches` 阶段被拦：

```
FAIL: [safe-delete][SAFE_DELETE_BULK_CONFIRM_REQUIRED]
{"count":53,"threshold":50,"targets":[".../rm-qianwen-l2-profile/Default/Extension Scripts"]}
```

清理脚本用 `rmSync(target, {recursive:true, force:true})` 删 Chrome 扩展缓存目录，
累计 53 项超过本机 50 项阈值。**我没有绕过守卫去递归删 `~/Library` 下的东西**——
改为把 profile 复制到 `/tmp/rm-l2-profile-copy-20261118`（28MB），
让脚本在副本上清缓存、跑浏览器。kimi 随即 8/8 通过，登录态正常。

原 profile 未被改写；副本留在 `/tmp`，不影响仓库。

### 4 · 结论：解冻前置的口径变化

用户原话是「解冻放在**全部验证跑通后**再处理」。现在：

- ✅ Pack 层：5/5 跑通。
- ✅ 冻结闸门：5 份回执留痕全对，本轮没碰冻结站。
- ❌ 会话重置层：4/5，qianwen 不满足。

N25 的 A/B 判据明确要求：

```
B 组回执 sessionResets[0].available === true && messageCountAfter < messageCountBefore
—— 否则 B 不能算「开了新会话」，这轮对照作废
```

如果冻结站也出现 qianwen 这种回落，**32 步真实发送跑完仍拿不到有效结论**。
所以我**不启动解冻**，先停在 N29。

## 残留

1. **N29 未诊断完成**。候选方向：qianwen adapter 的 `newChat` 选择器是否仍命中、
   「新对话」是否需要确认弹窗、消息列表选择器是否随页面改版失效。
   诊断须用 `new-session-probe.mjs` 在活跃站取证，**不得改判据来让 B 组通过**。
2. **N25 仍未解冻**，前置 4 条状态更新：dist 一致性已核（本轮重新 build）；
   5 站登录态已核；冻结站登录态仍未知（deepseek 从未预检，longcat 只有 11-10 旧快照）；
   32 步额度仍未确认。
3. **未改任何生产代码**；本轮只产出回执、报告与 N29 台账条目，全部落盘在 `/private/tmp/wt-g11`，
   尚未提交（等用户裁定下一步后一起提交）。
