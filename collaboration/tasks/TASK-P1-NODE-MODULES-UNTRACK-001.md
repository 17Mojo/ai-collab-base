---
task_id: TASK-P1-NODE-MODULES-UNTRACK-001
change_id: bugfix/no-spec
status: implementing
priority: P1
assignee: claude_code
assignee_role: AGENT_EXEC
reviewer: codearts_agent
primary_skill: api-test-pro
support_skills:
  - testing
  - documentation
created_at: 2026-10-25T18:00:00+08:00
acceptance_commands:
  - "python3 scripts/check_node_modules_untracked.py"
  - "python3 -m pytest tests/unit/test_check_node_modules_untracked.py -q"
  - "python3 -m pytest tests/ -q"
  - "python3 -m ruff check ."
  - "python3 scripts/scan_secrets_pii.py --workspace ."
result_file: collaboration/results/RESULT-P1-NODE-MODULES-UNTRACK-2026-10-25.md
---

# TASK-P1-NODE-MODULES-UNTRACK-001：node_modules 取消跟踪 + 依赖入库状态门禁

> **为什么独立成工单**：用户在批准执行顺序时明确要求
> 「C-1（node_modules）**必须独立成工单，不与缺陷修复混在一起**」。
> 本工单独立分支、独立 PR、独立门禁，与
> [`TASK-P1-REALMACHINE-COVERAGE-EXPAND-001`](TASK-P1-REALMACHINE-COVERAGE-EXPAND-001.md)
> 的真机缺陷修复**互不混杂**。

## 一、现状与真证

```bash
$ git ls-files chrome-extension/node_modules | wc -l
129
$ git ls-files chrome-extension/package-lock.json
chrome-extension/package-lock.json      # 锁文件已在库
$ du -sh .git
16M
```

`.gitignore` **早就**列了 `chrome-extension/node_modules/`（第 121 行）——
但 `.gitignore` 只影响未跟踪文件，**已跟踪的文件不会因为加进 ignore 就消失**。
所以这是一个「以为已经做了、其实没做」的状态。

## 二、代价（为什么值得单独做）

1. **仓库虚胖**：依赖代码与本仓源码混在同一个历史里，每次 clone 都要下载
   别人的依赖源码（本仓 777 个跟踪文件里 129 个是依赖）。
2. **密钥扫描器被噪音淹没**：2026-10-24 之前扫描器报 **251 条**命中，
   全部来自 node_modules 的压缩产物与源码标识符。真正的泄露被埋在噪音里，
   门禁因此形同虚设（那次的修法之一就是把 251 条降到 0）。
3. **依赖升级变成人肉合并**：依赖更新要同时改「真源码」和「入库的那份拷贝」，
   两份一旦不一致，谁也不知道哪份是对的。
4. **CI 根本用不上它**：CI 本来就自己 `npm ci`（`.github/workflows/test.yml`），
   入库那份拷贝**从来没被 CI 用过**。

## 三、两条不变量（缺一不可）

| | 不变量 | 少了它会怎样 |
|---|---|---|
| A | 任何 `node_modules/` 下的文件都**不得**被 git 跟踪 | 仓库继续虚胖，扫描器继续被噪音淹没 |
| B | 锁文件**必须**在版本库里 | `npm ci` 无法复现依赖版本，CI 每次装出来的依赖都可能不同 |

> 只做 A 不做 B，等于把「依赖版本不确定」这个**真问题**，
> 用「仓库小了」这个**假象**掩盖过去。所以门禁同时管这两条。

## 四、交付物

| 文件 | 作用 |
|---|---|
| `scripts/check_node_modules_untracked.py` | 门禁脚本：查 A 与 B，违规则非零退出 |
| `tests/unit/test_check_node_modules_untracked.py` | 门禁脚本自身的单测（含端到端：临时仓库造违规 → 必须拦下） |
| `.github/workflows/lint.yml` | 新增 `dependency-hygiene` 作业，把门禁接进 CI |
| `chrome-extension/node_modules/**` | 从索引中移除（`git rm -r --cached`），**文件本身保留在工作区** |

## 五、硬约束

1. **只取消跟踪，不删文件**：`git rm -r --cached`，
   本机 `node_modules` 继续可用，不需要重新 `npm install`。
2. **锁文件不许动**：`chrome-extension/package-lock.json` 必须在库。
3. **不与真机缺陷修复混提**：本工单的 diff 只含上表四个条目。

## 六、验收

见 frontmatter 的 `acceptance_commands`。结果文件：
[`collaboration/results/RESULT-P1-NODE-MODULES-UNTRACK-2026-10-25.md`](../results/RESULT-P1-NODE-MODULES-UNTRACK-2026-10-25.md)。
