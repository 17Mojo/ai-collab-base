# Change Proposal: Retire frozen A/B platforms (N25)

## Why

用户 2026-11-11 因「step_8 长会话撞墙」命题把 deepseek / longcat 冻结，
N25 登记「命题没有 A/B 对照、不可验」。2026-11-18 用户授权完整 A/B、
两站显式解冻后，只跑了 deepseek 两轮即裁定停止：

- A（无边界）/ B（有边界）**都撞在 `step_5_boundary`**，723.6s / 723.5s Response timeout；
- `fresh_session` 只声明在 `step_8_output`，两轮 `sessionResets=[]`，**都没跑到边界生效点**；
- 这不是「边界试过但无效」，而是「本轮不构成对命题的有效检验」。

用户据现场反自动化判断裁定 deepseek / longcat **不适合作为本项目目标网络源**，
N25 随之失去观察对象。需要把「停止 + 命题未获检验 + 目标源退出」落成可复核工件，
避免下游把 N25 关闭误读成「会话边界解掉了撞墙」。

## What Changes

- 新增结果报告 `RESULT-N25-AB-2026-11-18.md`：两轮回执表、判据逐条结算、
  根因分层（磁盘 timeout vs 现场反自动化判断）、活跃 5 站覆盖精度、风险与回滚。
- `known_gaps.json` N25 `open → closed`，改写标题/detail/fix 并追加 6 条证据；
  open 计数归零（29 closed / 1 wontfix）。
- `platform-freeze.mjs` 头部注释记裁定：两站降级为目标源外平台。
  **不改** `ACTIVE_PLATFORM_IDS`、`FROZEN_AB_PLATFORMS`、闸门语句——它们是变异锚点。
- deepseek A/B 两轮回执、变体 Pack、只读预检作为证据提交；longcat 两轮不执行、不留回执。
- spec delta：在 `active-platform-registry` 下新增「目标源退出」要求——平台退出目标源是
  治理定性，不删 adapter、不改白名单常量；平台冻结事实由代码闸门继续表达。

## 明确不在本 change 范围

- **不改白名单常量、不删生产 adapter**：deepseek / longcat 本就被闸门拦在活跃白名单外，
  「目标源外」是治理层追加的定性，重复表达会动到 3 处变异锚点。
- **不宣称命题成立或已解**：N25 关闭理由是「未获有效检验 + 目标源退出」，不是验证通过。
- **不写「实测证实反自动化」**：回执无验证码 / WAF / 风控信号，反自动化是用户现场判断。
- **不跑 longcat 两轮**：裁定停止，longcat 只有只读预检，不从 deepseek 外推。
- **不改 fresh_session 机制与 A/B 判据**：保留能力，只是本轮不继续验。

## 验收标准（可机器判定）

1. A/B 两轮回执存在且如实记录 `success=false` / `4/5` / `step_5_boundary` / `sessionResets=[]`。
2. longcat 无 `L2-longcat-*.ab-*.json` 回执；plan 文件保持 plan-only，4 条命令只执行 2 条。
3. `openspec validate retire-frozen-ab-platforms --strict` 零错误，归档后 archived 校验零错误。
4. `platform-freeze.test.mjs` 全绿，白名单仍 5 站，变异检查 125/125 被杀死。
5. `known_gaps.json` N25 closed 且保留条目；open 为 0。
6. 结果报告含四段（执行命令 / 验证结果 / 风险 / 回滚）与可解析状态行。

## 实测证据

见 `collaboration/results/RESULT-N25-AB-2026-11-18.md` 与 tasks.md 的 E 编号。
