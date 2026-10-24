---
name: OpenSpec CLI 1.11.0 的 legacy 边界与本仓现行接线形态
description: 2026-10-24 实测——openspec 1.11.0 把 openspec/AGENTS.md 当 legacy 并在 init --force 时删除，根 CLAUDE.md 的 OPENSPEC:START/END managed block 也是 legacy（1.11.0 主动删除它）；本仓现行形态是 openspec/config.yaml + .claude/skills/openspec-* + .codeartsdoer/skills/openspec-*
type: project
from: Agent
---

## 事实（2026-10-24 在临时目录实测，非推断）

本机 openspec CLI 版本 **1.11.0**（官方已到 1.15.0，未升级）。它的行为边界：

| 事实 | 实测方式 |
|---|---|
| `openspec/AGENTS.md` 是 **legacy**：`openspec init --force` 把它当 "obsolete workflow file" **直接删除** | 临时目录建该文件 → init --force → 文件消失 |
| 根 `CLAUDE.md` 里的 `<!-- OPENSPEC:START -->…<!-- OPENSPEC:END -->` 块也是 legacy：1.11.0 **主动删除**它（本仓 CLAUDE.md 那段就是被它删掉的） | 在本仓跑 init → git diff CLAUDE.md 出现删除 |
| 1.11.0 **不**往根 CLAUDE.md/AGENTS.md 注入 managed block，指令改为随技能分发 | init 后 CLAUDE.md 无新增块，改为生成 .claude/skills/ 与 .claude/commands/ |
| `openspec update --force` 只删 marker 块，**不动无 marker 的普通段落** | 临时目录同时放 marker 块与普通段落 → update --force → 只 marker 块被删 |
| `openspec doctor` 判 root 健康与否看 **`openspec/config.yaml` 在不在**（缺 → unhealthy） | 装前 doctor 报 unhealthy，装后 ok |

## 本仓现行接线形态（2026-10-24 落地）

- `openspec/config.yaml` —— 项目上下文 + 各工件规则（proposal/specs/design/tasks）+ apply/archive 操作指引。
  **注意**：`rules` 与 `operations.*.guidance` 的值必须是**字符串数组**，写成块标量会被
  doctor 忽略并打印 "must be an array of strings"。
- `.claude/skills/openspec-*/SKILL.md`（6 个）+ `.claude/commands/opsx/*.md`（6 个）——进版本库。
- `.codeartsdoer/skills/openspec-*/SKILL.md` —— CodeArts 侧同名技能；该目录被
  `.gitignore` 忽略（.gitignore:117），**不进版本库**，只在本机仓库副本生效。
- CLAUDE.md 里的 OpenSpec 段落**故意不带 marker**，这样 `openspec update` 不会删它。

## Why

CLAUDE.md 原先那段 managed block 让 agent 必读 `@/openspec/AGENTS.md`，但该文件
**本仓从未存在过**（git 全history 无此文件），且按现行 CLI 下一次 `init --force`
还会被删——是一个**会腐烂的指针**。实测清楚了边界才决定不按原字面创建它。

## How to apply

1. 升级 openspec CLI 或跑 `openspec init --force` 前，先确认 `openspec/AGENTS.md`
   不会被当成 legacy 删掉；1.11.0 下**不要**往那个路径放指令。
2. 改 CLAUDE.md 里的 OpenSpec 段落时**不要**加 `<!-- OPENSPEC:START/END -->` marker——
   加了就会被 `openspec update` 删掉。
3. 工件格式以 `openspec instructions <artifact> --change <id>` 的输出为准，别凭印象写；
   `openspec validate <id> --strict` 是硬门禁。
4. 本仓唯一变更 `add-concurrent-workspace-guard` 已补齐 4/4 工件（proposal / specs / design / tasks）。

**相关**：[[feedback_ci_isolation_trap]]、[[project_cli_exit_code]]
