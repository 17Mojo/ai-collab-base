# Change Proposal: Replace qianwen with stepfun

## Why

用户 2026-11-18 裁定：「qianwen 有防范非人类操作机制，替换成 stepfun
（https://studio.stepfun.com/，我配合你登录）」。

N29 的修复证明千问的会话重置入口可以被正确选中，但那是**产品代码层的结论**，
不能推翻「这台站点不适合继续做真机自动化回归」的裁定。反自动化机制会让真机结果
随站点风控策略漂移，证据不可复现——继续把它留在活跃白名单里，等于拿不可复现的
样本当回归基线。

## What Changes

- 真人登录 stepfun 后做只读 DOM 探测，确定输入框 / 发送 / 消息 / 新对话选择器。
- 新增 `src/platforms/stepfun-adapter.js`，并在 `tests/platforms.mjs`、
  `manifest.json`（host_permissions + content_scripts.matches）、
  `src/content/content-script.js`、`src/background/service-worker.js` 登记域名与适配器。
- 新增模拟 fixture、真实快照采集记录，更新平台注册守护从 10 站 → 11 站。
- `tests/real-machine/platform-freeze.mjs` 的活跃白名单 qianwen → stepfun，
  同步 `platform-freeze.test.mjs` 与 `mutation-check.mjs` 的变异锚。
  qianwen adapter 保留在生产层，但本轮真机不再碰它；deepseek / longcat 仍冻结。
- `known_gaps.json` 新增 N30 记录裁定、假阳性登录检测与实测证据。

## 明确不在本 change 范围

- **不删 qianwen adapter**：生产层仍支持该站，只是不进活跃真机白名单。
- **不绕验证码 / 风控**：登录由真人在窗口里完成，脚本只检测状态。
- **不改 A/B 判据、不启动冻结站发送**。
- **不把首次 login-helper 的假阳性证据删掉**：如实留档，写清为什么它不算登录证据。

## 验收标准（可机器判定）

1. stepfun 登录态有真人确认标记 + 账号信号（localStorage 身份键），
   不是「首页有输入框就算登录」的假阳性。
2. 11 站注册一致性：每个平台都有 adapter / fixture / hostname 登记；
   `getAdapter()` 能从 stepfun URL 认出适配器。
3. 扩展全套 326 条、适配器矩阵 117/125 passed / 0 failed / 8 skipped、
   变异检查 125/125 被杀死。
4. stepfun 完整 L2 8/8，`sessionResets[0].available === true && after < before`，
   `platformPolicy.unfrozenBy === null`。
5. 其余 4 个活跃站复验无回归，冻结站未被触碰。
