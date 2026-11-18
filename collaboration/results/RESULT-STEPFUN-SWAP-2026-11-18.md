# RESULT — 用 stepfun 替换 qianwen 作为活跃真机站（2026-11-18）

- **状态**: completed（用户裁定落地；活跃 5 站替换后全部复验通过）
- 日期：2026-11-18
- 执行者：`claude_code`（AGENT_EXEC）
- 口径：本轮**没有**解冻 deepseek / longcat；qianwen adapter 保留在生产层，但真机不再碰

> 用户原话：「qianwen 有防范非人类操作机制，替换成 stepfun
> （https://studio.stepfun.com/ 我配合你登陆）」。

## 1 · 登录事实：先纠正一次假阳性

第一轮 `login-helper.mjs` 1 秒就报 stepfun「已登录」——因为游客态首页也有
`textarea`，脚本把它当 composer，页面又没有旧站点那几句登录提示。
这次判定**不算证据**，两份 `login-stepfun-2026-11-18*.json` 如实留档不删。

改为「真人确认标记 + 账号信号」后重采：

- 真人登录后回话确认，脚本写入确认标记；
- `login-stepfun-2026-11-18.human.json` 记录 `url=https://studio.stepfun.com/`、
  `loginCta=false`、localStorage 含 `studio_user_login_recorded` 与用户标识键；
- 页面侧栏可见账号名与「我的资产库 / 会话」等已登录结构。

登录全程由真人在窗口完成；脚本不点发送、不导入 Pack、不绕验证码。

## 2 · 只读 DOM 取证

| 角色 | 生产选择器 | 证据 |
|---|---|---|
| 输入框 | `textarea[data-slot="textarea"]` | 登录态首页唯一命中 |
| 发送 | `button[aria-label="发送"]` | 实际点它发了 1 条短消息（见下） |
| 消息 | `[data-split-pane="chat"] div[class="flex flex-col gap-6"] > div` | 2 条消息→2 节点；新对话后 0 |
| 新对话 | 侧栏「新对话」button | 点击后消息 2→0、URL 回 `/` |

输入区旁的 `button[aria-label="新会话"]` 是下拉菜单（模型/会话选择），
**不是**开新会话入口——没有写进 adapter 的 `newChat`。

为验证消息计数契约，只在真人账号上发过两条短提示（`连接器自检A1/A2`），
没有跑 Pack、没有消耗 32 步额度。截图：`stepfun-message-probe-2026-11-18.png`。

## 3 · 代码与登记

新增 `src/platforms/stepfun-adapter.js`；同步登记到：

- `tests/platforms.mjs`（第 11 站）
- `manifest.json` 的 `host_permissions` 与 `content_scripts.matches`
- `src/content/content-script.js` 的 `PLATFORM_CONFIGS`
- `src/background/service-worker.js` 的 `adapters`
- `tests/adapter-matrix/fixtures/mock-dom-stepfun.html`
- `tests/real-machine/fixtures/real/stepfun.{json,html}`（快照采集器真实产物）

活跃白名单 `ACTIVE_PLATFORM_IDS`：`qianwen` → `stepfun`；
`platform-freeze.test.mjs` 与 `mutation-check.mjs` 的锚点同步改掉。
`known_gaps.json` N30 关闭；29→30 条，open 只剩 N25（冻结站 A/B）。

> 快照采集器用无 profile 的浏览器，采到的是 stepfun 游客态首页（messageCount=0），
> 这是它如实留下的边界；选择器契约的真机依据来自上面第 2 节的登录态探针，
> 不把游客态快照冒充成登录态会话快照。

## 4 · 验证

| 项 | 结果 |
|---|---|
| 扩展全套 | 326 / 326 |
| 适配器矩阵 | 117 passed / 0 failed / 8 skipped（11 站） |
| 变异检查 | 125 / 125 被杀死（含白名单锚点） |
| 平台注册一致性 | 11 站，adapter / fixture / hostname 全对齐 |
| 后台 `getAdapter()` | stepfun URL 能认出适配器 |

活跃 5 站（替换后）真机：

| 平台 | success | steps | 会话重置 | 策略 | 消息数 | unfrozenBy |
|---|---|---|---|---|---|---|
| stepfun | true | 8/8 | true | text-match | 12→0 | null |
| yuanbao | true | 8/8 | true | adapter-selector | 12→0 | null |
| chatglm | true | 8/8 | true | adapter-selector | 12→0 | null |
| yiyan | true | 8/8 | true | adapter-selector | 6→0 | null |
| kimi | true | 8/8 | true | adapter-selector | 6→0 | null |

`ALL PASS: True`。冻结站在本轮 stepfun 验证中未被触碰，没有
`ALLOW_FROZEN=1` 的发送；此前完成过一次**只读**登录态预检
（`L2-precheck-2026-11-18.frozen2.json`，两站 composer 可见、未发包），
A/B 的 32 步真实发送仍未启动。

## 5 · 边界

- qianwen 的 N29 修复仍有效（活动站证据已由 stepfun 接替），但不再用 qianwen
  做真机回归；旧报告里「活跃 5 站含 qianwen」的清单自本轮起不再适用。
- stepfun 的消息容器依赖 Tailwind 实用类名（`flex flex-col gap-6`）与
  `[data-split-pane="chat"]` 结构，站点改版时需要重跑 DOM 探针；这是已知脆弱点，
  不是「跨发版稳定选择器」。
- N25 的冻结站 A/B 仍未启动；用户上一条问询未选择启动方式，因此停在预检完成状态。

## acceptance_commands

```bash
cd chrome-extension
CODEBUDDY_SAFE_DELETE_ENABLED=0 npm test                    # 326/326
CODEBUDDY_SAFE_DELETE_ENABLED=0 npm run test:adapters        # 0 failed
CODEBUDDY_SAFE_DELETE_ENABLED=0 node tests/real-machine/mutation-check.mjs

python3 - <<'PY'
import json, pathlib
base = pathlib.Path('collaboration/results/real-machine-runs/evidence')
names = {'stepfun': 'L2-stepfun-auto-2026-11-18.full8.json',
         **{p: f'L2-{p}-auto-2026-11-18.swap.full8.json'
            for p in ['yuanbao','chatglm','yiyan','kimi']}}
for p, n in names.items():
    d = json.loads((base/n).read_text()); e=d['exec']; r=e['result']; sr=r['sessionResets'][0]
    print(p, e['success'], len(r['steps']), sr['available'], sr['strategy'],
          sr['messageCountBefore'], sr['messageCountAfter'], d['platformPolicy']['unfrozenBy'])
PY

openspec validate replace-qianwen-with-stepfun --strict
```
