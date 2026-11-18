# Implementation Tasks

> 凡勾选者必须附**实测证据（命令 + 关键输出）**，不写「已完成」了事。

## Phase 0 · 立项与登录事实

- [x] 0.1 产出 proposal / spec delta / tasks（E1）
- [x] 0.2 纠正 login-helper 的首轮假阳性，用真人确认标记重采登录态（E2）
- [x] 0.3 `openspec validate replace-qianwen-with-stepfun --strict` 零错误（E1）

## Phase 1 · DOM 取证与生产登记

- [x] 1.1 登录态只读 DOM 探针确定输入框 / 发送 / 消息 / 新对话选择器（E3）
- [x] 1.2 新增 stepfun adapter + 模拟 fixture + 真实快照记录（E4）
- [x] 1.3 manifest / content-script / service-worker / platforms 同步登记第 11 站（E4）

## Phase 2 · 白名单替换

- [x] 2.1 `ACTIVE_PLATFORM_IDS` qianwen → stepfun，qianwen adapter 保留（E5）
- [x] 2.2 `platform-freeze.test.mjs` 与 `mutation-check.mjs` 锚点同步（E5）
- [x] 2.3 `known_gaps.json` 新增并关闭 N30（E6）

## Phase 3 · 验证与收口

- [x] 3.1 扩展全套 326/326、矩阵 117/125 passed / 0 failed、变异 125/125（E7）
- [x] 3.2 stepfun 完整 L2 8/8、会话重置 12→0、unfrozenBy=null（E8）
- [x] 3.3 其余 4 站复验无回归，冻结站零触碰（E8）
- [x] 3.4 提交带 pathspec、PR、合入登记、归档、`validate --archived --strict`（E9）

## 实测证据

### E1 · 工件

```
openspec/changes/replace-qianwen-with-stepfun/{proposal.md,tasks.md,
  specs/active-platform-registry/spec.md}
$ openspec validate replace-qianwen-with-stepfun --strict
Change 'replace-qianwen-with-stepfun' is valid
```

### E2 · 登录事实（含假阳性更正）

```
首次: login-stepfun-2026-11-18.json / .waiting.json
     1 秒报已登录 —— 游客态首页也有输入框，判定不可信，留档不删
重采: login-stepfun-2026-11-18.human.json
     url=https://studio.stepfun.com/, loginCta=false
     localStorage: studio_user_login_recorded + 用户标识键
     真人回话确认后才写 confirmation sentinel
```

### E3 · 只读 DOM + 短消息探针

```
textarea[data-slot="textarea"]                                   → 1
button[aria-label="发送"]                                        → 1
[data-split-pane="chat"] div[class="flex flex-col gap-6"] > div  → 2（2 条消息）
点侧栏「新对话」后                                                → 0
诱饵 button[aria-label="新会话"] 是下拉，不写进 newChat
证据: stepfun-message-probe-2026-11-18.png
```

### E4 · 第 11 站登记

```
新增 src/platforms/stepfun-adapter.js
新增 tests/adapter-matrix/fixtures/mock-dom-stepfun.html
新增 tests/real-machine/fixtures/real/stepfun.json / stepfun.html
同步 tests/platforms.mjs、manifest.json（2 处）、content-script.js、
service-worker.js；平台注册守护 10 → 11
```

### E5 · 白名单替换

```
ACTIVE_PLATFORM_IDS = [stepfun, yuanbao, chatglm, yiyan, kimi]
FROZEN_AB_PLATFORMS = [deepseek, longcat]
qianwen adapter 仍在 src/platforms/ 且注册一致性通过，但 PLATFORM=qianwen 默认被拒
platform-freeze.test.mjs 期望列表改为 ["chatglm","kimi","stepfun","yiyan","yuanbao"]
mutation-check 的 deepseek 注入锚点改为以 "stepfun" 开头
```

### E6 · 台账

```
N30 status=closed closed_at=2026-11-18
30 条: closed 28 / wontfix 1 / open 1（仅 N25）
```

### E7 · 全集守护

```
扩展全套                 326 / 326 passed
适配器矩阵               117 passed / 0 failed / 8 skipped（11 站）
变异检查                 125 / 125 被杀死
getAdapter(stepfun URL)  能认出适配器
```

### E8 · 活跃 5 站真机

```
stepfun  True 8/8 True text-match          12→0 unfrozenBy=null
yuanbao  True 8/8 True adapter-selector   12→0 unfrozenBy=null
chatglm  True 8/8 True adapter-selector   12→0 unfrozenBy=null
yiyan    True 8/8 True adapter-selector    6→0 unfrozenBy=null
kimi     True 8/8 True adapter-selector    6→0 unfrozenBy=null
ALL PASS: True
```

结论报告：`collaboration/results/RESULT-STEPFUN-SWAP-2026-11-18.md`。

### E9 · 合入留痕

```
PR #78: https://github.com/17Mojo/ai-collab-base/pull/78
合入提交（40 位完整 sha）: 718dde192f5df3cafc063ccaef3816903c3074d6
同一合入提交登记了两个 change_id：
  fix-qianwen-visible-semantic-control / replace-qianwen-with-stepfun
```
