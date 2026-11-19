## ADDED Requirements

### Requirement: 解冻必须来自用户裁定原文，提案本身不构成授权

`openspec` change 提案 SHALL 只表达「拟做什么」，不得被当作解冻授权。在用户给出
点名平台与允许范围的裁定原文之前，deepseek MUST NOT 进入 `ACTIVE_PLATFORM_IDS`，
真机驱动 MUST NOT 带 `ALLOW_FROZEN=1` 放行它，实施任务 MUST 保持未完成状态。

#### Scenario: 只有提案、没有裁定原文

- **WHEN** `unfreeze-deepseek` 提案已立项并通过 `--strict` 校验，但用户裁定原文尚未落档
- **THEN** 唯一事实源 `ACTIVE_PLATFORM_IDS` MUST NOT 含 deepseek
- **AND** `PLATFORM=deepseek` MUST 被冻结闸门默认拒绝
- **AND** 本 change 的 P1–P4 任务 MUST 全部未勾选
- **AND** 任何 L2 回执里 MUST NOT 出现 `unfrozenBy="ALLOW_FROZEN=1"`

#### Scenario: 裁定原文落档后

- **WHEN** 用户裁定原文（点名 deepseek + 允许范围 + 时间）已落档为证据
- **THEN** 白名单常量才允许变更，且 `AB_PLATFORMS ⊆ FROZEN_AB_PLATFORMS` 不变式仍成立
- **AND** P4 回执 MUST 满足 `active === true && unfrozenBy === null`
- **AND** 真机命令 MUST NOT 带 `ALLOW_FROZEN=1`

### Requirement: 解冻的测试改判只能换样例，不能删断言

白名单变更会让绑定 deepseek 的既有断言变红。这些断言 SHALL 改换成仍在冻结集里的站，
MUST NOT 通过删除断言、放宽为恒真、或把它们改成「按新常量推导后必然成立」来消红。
`AB_PLATFORMS` 推导式只适用于**轮数与命令数**这类随实验设计变化的量。

#### Scenario: 4 条冻结站样例断言

- **WHEN** deepseek 移出冻结集、`tests/platform-freeze.test.mjs` 出现 4 条红
- **THEN** `:30` 的白名单计数断言更新为新站数，断言本身保留
- **AND** `:40` / `:139` / `:155` 的「冻结站样例」换成仍在冻结集里的站
- **AND** 变异锚里绑定旧常量值的 `find` 串同步改写
- **AND** 改后若这 4 条断言被整体删除，变异检查 MUST NOT 被当作验收通过

### Requirement: 反自动化空白必须按跨站口径陈述

解冻报告 MUST NOT 声称反自动化维度已验证，或暗示它是 deepseek 特有的问题。
已知阳性样本（L1 的 6 条 `bot_check`）全部来自 chatgpt / claude 两个非活跃站；
5 个活跃站与 deepseek 一样没有基线。`captchaBypass: false` 是行为声明而非阴性观测，
MUST NOT 被写成「没有遇到验证码」。

#### Scenario: 交付说明里的反自动化段落

- **WHEN** 解冻 RESULT 或交付摘要描述验证范围
- **THEN** 该段落 MUST 写清反自动化不在本次范围，且 5 个活跃站同样没有基线
- **AND** MUST NOT 出现「反自动化已验过」「无验证码即无风控」或等价措辞
- **AND** MUST 引用 `known_gaps.json` 的 N61

### Requirement: 历史计划工件只读留档

由 `session-wall-ab.mjs` 产出的计划与变体 Pack 文件名只带日期。同一天重跑
MUST NOT 覆盖已有且内容不同的工件；任一目标要被覆盖时，全部目标 MUST 不被写入，
并以非零退出码退出。显式放行 `FORCE_OVERWRITE=1` 才能覆盖。

#### Scenario: 重跑撞上已有工件

- **WHEN** 计划或任一变体包路径已存在内容不同的文件，且未给 `FORCE_OVERWRITE=1`
- **THEN** 脚本 MUST 退出码 2 并点名被挡下的目标
- **AND** 所有目标文件 MUST 保持原样（含 mtime）
- **AND** 两份历史计划 `session-wall-ab-plan-2026-11-11/11-18.json` MUST NOT 被当作待执行计划
