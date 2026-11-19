# Change Proposal: Unfreeze deepseek（plan-only — 待用户裁定）

> **状态：提案，不是授权。** 用户尚未给出「点名 deepseek + 允许范围」的解冻裁定原文。
> 本提案只完成 P0（工件与校验）；`tasks.md` 里 P1–P4 一律**未勾选、未执行**。
> 拿到裁定原文之前，`ACTIVE_PLATFORM_IDS` 不含 deepseek，任何真机命令都不许带
> `ALLOW_FROZEN=1`。**提案通过 ≠ 解冻生效。**

## Why

用户 2026-11-11 红线：仅保留 qianwen / yuanbao / chatglm / yiyan / kimi，其他冻结不去碰。
2026-11-18 两站显式解冻后只跑了 deepseek 两轮：A / B 都撞在 `step_5_boundary`
（723.6s / 723.5s Response timeout），而 `fresh_session` 只声明在 `step_8_output`，
两轮 `sessionResets=[]`，**都没跑到边界生效点**。用户据现场反自动化判断裁定停止，
deepseek / longcat 降级为目标源外平台（N25 closed，含义是「未获有效检验 + 目标源退出」，
**不是**「会话边界解掉了撞墙」）。

解冻前的准备已完成，见 `collaboration/results/PLAN-UNFREEZE-DEEPSEEK-2026-11-19.md` §5：

- **A（P7 发送链路）**：A1 对账把假绿变红；A2 删掉 mock fixture 里真机不存在的假发送按钮，
  改成显式声明 `none` + 真机快照当独立见证人；A3 清空 4 条从未命中的死选择器，
  把 Enter 兜底变成有守护的主路径（7 用例 / 4 变异锚）。N54 closed，
  但**发送区 DOM 仍无工件**（N60 open）。
- **B（A/B 计划解耦）**：拆出 `AB_PLATFORMS`（实验设计）与 `FROZEN_AB_PLATFORMS`
  （治理事实），不变式是子集；写死的轮数改成推导；两份 4 命令计划工件退役为只读留档，
  脚本默认拒绝覆盖历史证据。
- **C（P8 反自动化）**：登记 N61 跨站空白。复核时更正了 PLAN 原稿「零阳性样本」的说法：
  L1 有 6 条 `bot_check` 阳性，但**全在 chatgpt / claude 两个非活跃站**；5 个活跃站
  与 deepseek 同样没有基线。

当前可复核的基线：单测 **413**、适配器矩阵 **108/125**（0 failed / 17 skipped）、
全量变异 **178/178 被杀死**、台账 **61 条**（53 closed / 7 open / 1 wontfix）、
未解冻基线工作区全绿。

## What Changes

**P0（本提案，已完成）**

- 产出 `proposal.md` / `tasks.md` / `specs/active-platform-registry/spec.md`，
  `openspec validate unfreeze-deepseek --strict` 零错误。
- 把 C 段的「不在范围」落成提案文本（下文）。

**P1（需用户裁定原文 + N60 的单独放行）**

- 用户裁定原文落档：点名平台 + 允许范围 + 时间。没有原文不进 P2。
- N60：对 `https://chat.deepseek.com/` 跑**只读**探针（不发消息 / 不输入 / 不点发送），
  把输入区容器 `outerHTML` 与祖先 3 层落盘，回填 N54 的形状描述。
  这一步属于冻结站操作，**需单独放行**；不放行则解冻仍按「发送区无工件」继续执行，
  但交付说明必须如实写出这个空白。

**P2（裁定后：常量与门禁同步）**

- `ACTIVE_PLATFORM_IDS` 加入 deepseek；`FROZEN_AB_PLATFORMS` 移除 deepseek；
  `AB_PLATFORMS` 同步（它必须保持是冻结样本集的子集）。
- `tests/platform-freeze.test.mjs` 的 4 条断言改判，不能删：
  ① `:30` 白名单恰好 5 站 → 6 站；② `:40` 冻结站默认拒绝的样例从 deepseek / longcat
  换成仍在冻结集里的站；③④ `:139` / `:155` N35 预检与解冻留痕用例的「冻结站样例」
  同样换站。**改样例而不是删断言**——删了等于把守门拆了。
- `tests/real-machine/mutation-check.mjs` 里绑定旧常量值的 `find` 串同步改写，
  否则报「变异描述与代码脱节」而不是「测试没红」（PLAN §2.3 预警过，B1/B2 已吃过一次）。

**P3（裁定后：离线门禁）**

- 9 条前置断言全绿（P2 后 `platform-freeze.test.mjs` 应恢复 0 红）。
- 扩展全套、适配器矩阵、全量变异复核；`dist` 与源码一致性按构建口径核
  （这是构建一致性检查，**不是** PROTOCOL §14.5 的门禁——N38 已更正过这条误引用）。

**P4（裁定后：真机验收）**

- **不带 `ALLOW_FROZEN`** 跑 deepseek 8/8；回执须
  `platformPolicy.active === true && unfrozenBy === null`。
- 5 个活跃站各跑一轮无回归；longcat 零触碰（回执里不应出现 longcat）。
- RESULT + `known_gaps` 登记裁定时间 / 依据 / 实测数字 → 归档 →
  `openspec validate unfreeze-deepseek --archived --strict`。

## 明确不在本 change 范围

- **反自动化维度（N61）**：不在本次验证内，且**不是 deepseek 特有**——5 个活跃站同样
  没有基线；L1 那 6 条 `bot_check` 阳性只说明 chatgpt / claude 两个非活跃站被平台侧拦过。
  交付说明里不许出现「反自动化已验过」。
- **不碰 longcat**：它仍是冻结样本集里的实验对象，11-12 两轮数据无效，另案处理。
- **不删任何 adapter**：生产支持与真机白名单是两件事。
- **不绕验证码 / 风控**，不替真人登录。
- **不把 N25 写成已解决**：它的 closed 理由是「未获有效检验 + 目标源退出」。
- **不补采 N60 的发送区 DOM**，除非用户单独放行只读探针。
- **不改 A/B 判据**：变体 Pack、会话重置判据保持原样。
- **不覆盖两份历史计划工件**：`session-wall-ab-plan-2026-11-11/11-18.json` 只读留档，
  重跑默认拒绝覆盖。

## 验收标准（可机器判定）

1. 本提案三工件存在；`openspec validate unfreeze-deepseek --strict` 零错误。
2. **裁定原文未落档前**：`ACTIVE_PLATFORM_IDS` 不含 deepseek；
   `PLATFORM=deepseek` 默认被闸门拒绝；`tasks.md` 的 P1–P4 全部未勾选。
3. 裁定原文落档后：P2 改常量，**4 条测试断言仍然在（只是换样例）**，
   不是通过删断言变绿；`AB_PLATFORMS ⊆ FROZEN_AB_PLATFORMS` 不变式仍成立。
4. P3 全绿：单测 / 矩阵 / 变异数字不低于本提案记录的 413 / 108/125 / 178。
5. P4 回执：`active === true && unfrozenBy === null`，命令里没有 `ALLOW_FROZEN=1`；
   5 个活跃站无回归；longcat 零触碰。
6. 归档后 `openspec validate unfreeze-deepseek --archived --strict` 零错误。

## 实测证据

见 `tasks.md` 的 P0 段与 `collaboration/results/PLAN-UNFREEZE-DEEPSEEK-2026-11-19.md` §5。
