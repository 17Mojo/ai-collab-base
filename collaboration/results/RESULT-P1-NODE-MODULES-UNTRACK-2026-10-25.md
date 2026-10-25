# RESULT-P1-NODE-MODULES-UNTRACK-2026-10-25

**状态**: completed
**任务**: `TASK-P1-NODE-MODULES-UNTRACK-001`（node_modules 取消跟踪 + 依赖入库状态门禁）
**执行**: Claude Code（AGENT_EXEC）　**复核**: CodeArts（AGENT_TEST）
**分支**: `chore/untrack-node-modules`（基线 `main` @ `71c9eac`）
**日期**: 2026-10-25

> **独立成工单**：用户在批准执行顺序时明确要求
> 「C-1（node_modules）**必须独立成工单，不与缺陷修复混在一起**」。
> 本工单走独立分支、独立 worktree、独立 PR，
> 与 [`TASK-P1-REALMACHINE-COVERAGE-EXPAND-001`](./RESULT-P1-REALMACHINE-COVERAGE-EXPAND-2026-10-25.md)
> 的真机缺陷修复互不混杂。

---

## 一句话结论

`node_modules` 里的 129 个文件（4.9 MB）被取消跟踪，工作区检出的内容从 16.0 MB 降到 11.1 MB（**-31%**）；
新增门禁脚本把「node_modules 不得入库 **且** 锁文件必须在库」这两条不变量接进 CI，
并配了 12 条单测（含端到端：造违规仓库 → 必须拦下）。

---

## 执行命令

以下 5 条即工单契约里的 `acceptance_commands`，逐字执行，全部通过：

### 1. `python3 scripts/check_node_modules_untracked.py`

```
[OK] 依赖入库状态合规：648 个被跟踪文件中 0 个落在 node_modules 下，1 个锁文件均在库。
```

### 2. `python3 -m pytest tests/unit/test_check_node_modules_untracked.py -q`

```
12 passed in 0.54s
```

### 3. `python3 -m pytest tests/ -q`

```
3048 passed, 7 skipped in 40.80s
```

7 个 skip 全部是环境原因：5 个本地后端未启动（`127.0.0.1:8000`）、
1 个 worktree 里没有 `local-backend/data/client_tokens.db`、
1 个 worktree 里没有 gitignore 掉的 `.trae/skills`。**都不是代码问题**。

> 注：本工单在独立 worktree 中执行，比主工作区多 1 个 skip——
> worktree 是全新检出，不含 gitignore 掉的本地产物。

### 4. `python3 -m ruff check .`

```
All checks passed!
```

### 5. `python3 scripts/scan_secrets_pii.py --workspace .`

```
[OK] no secrets found
```

---

## 验证结果

### 变更内容

| 项 | 之前 | 之后 |
|---|---|---|
| 被跟踪的 `node_modules` 文件 | 129 个 / 4.9 MB | **0 个** |
| 锁文件 `chrome-extension/package-lock.json` | 在库 | **仍在库**（不许动） |
| 工作区检出的内容总体积 | 16.0 MB | **11.1 MB（-31%）** |
| `.git` 历史体积 | 16 MB（size-pack 2.94 MiB） | 16 MB（**不变**——见「风险」） |

变更方式：`git rm -r --cached chrome-extension/node_modules`
——**只取消跟踪，不删文件**，本机 `node_modules` 继续可用，不需要重新 `npm install`。

### 交付物

| 文件 | 作用 |
|---|---|
| `scripts/check_node_modules_untracked.py` | 门禁脚本：管两条不变量，违规则非零退出 |
| `tests/unit/test_check_node_modules_untracked.py` | 门禁脚本自身的 12 条单测 |
| `.github/workflows/lint.yml` | 新增 `dependency-hygiene` 作业，把门禁接进 CI |
| `chrome-extension/node_modules/**` | 从索引移除（129 文件 / 13.3k 行删除） |

### 两条不变量为什么必须同时管

| | 不变量 | 少了它会怎样 |
|---|---|---|
| A | 任何 `node_modules/` 下的文件都**不得**被 git 跟踪 | 仓库继续虚胖，密钥扫描器继续被噪音淹没 |
| B | 锁文件**必须**在版本库里 | `npm ci` 无法复现依赖版本，CI 每次装出来的依赖都可能不同 |

> 只做 A 不做 B，等于把「依赖版本不确定」这个**真问题**，
> 用「仓库小了」这个**假象**掩盖过去。门禁脚本同时查这两条。

### CI 接线

`.github/workflows/lint.yml` 新增 `dependency-hygiene` 作业：

```yaml
  dependency-hygiene:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - name: Check node_modules is untracked (and lockfiles are present)
        run: |
          python scripts/check_node_modules_untracked.py
```

该作业**不装任何依赖**（脚本只用标准库 `subprocess`/`pathlib`），
因此不受 `npm ci` 成功与否影响，也不会因为网络问题误报。

### 门禁脚本自身被测过

12 条单测里包含**端到端**用例：临时造两个仓库——
一个把 `node_modules` 加进索引（门禁必须返回 1），一个只加锁文件（门禁必须返回 0）。
判定逻辑的边界也逐条钉住：

- `src/node_modules_helper.js`（名字里带 `node_modules` 但**不是目录**）不算违规；
- 嵌套目录 `tests/playwright/node_modules/...` 同样会被挑出来。

---

## 测试结论

**结论：通过。**

- 5 条验收命令全部执行通过（见上，逐条附实际输出）；
- 门禁脚本单测 **12/12** 通过；
- Python 全量 **3048 通过 / 7 跳过 / 0 失败**（跳过均为环境原因）；
- ruff **All checks passed**；密钥扫描 **0 命中**。

门禁在真实仓库上的表现已实测：取消跟踪前它会拦下（129 个文件），
取消跟踪后报 `[OK]`——**不是写完就没再验证过**。

---

## 风险

### `.git` 历史体积不会因此缩小（如实说明）

`git rm --cached` 只改索引，**历史里的 blob 仍在**，所以 `.git` 仍是 16 MB
（size-pack 2.94 MiB），**克隆体积不会因为这个提交而变小**。

真正变小的是**工作区检出内容**（16.0 MB → 11.1 MB）和**未来的提交/diff**
（依赖更新不再需要同时改「真源码」和「入库的那份拷贝」）。

要真正瘦身历史需要 `git filter-repo` 重写历史——**本工单不做**：
重写会改写所有 commit id、影响所有协作者的分支，代价与风险远大于收益，
且会让「历史里曾有过这份拷贝」的事实消失。

### 密钥扫描器的收益已被前一个工单吃掉

2026-10-24 的体检工单已经把扫描器改造到 **0 命中**（237 条误报 → 0）。
因此本工单对扫描器是**锦上添花**（从此扫描面里彻底没有依赖产物），
不是修 bug。**不夸大收益。**

### 协作者的本地状态

`git rm --cached` **不删工作区文件**，所以其他协作者拉取本分支后，
本地 `node_modules` 仍在，无需重新安装。若有人本地已经删了 `node_modules`，
拉取后跑 `npm ci` 即可（锁文件在库，版本可复现）。

### 与本工单无关但会被本 PR 触及的

`chrome-extension/node_modules/.package-lock.json` 在**主工作区**有一个
**本工单之外的**未提交改动（会话开始前就存在）。**未纳入本工单**——
按共享工作区规则只提交自己的文件。

---

## 回滚

本工单不涉及数据迁移、不改 schema、不改运行时配置，回滚成本低。

| 场景 | 回滚方式 |
|---|---|
| 整体回滚 | `git revert` 本工单提交（PR 未合入前直接删分支 `chore/untrack-node-modules` 即可） |
| 只回滚门禁接线 | 撤掉 `lint.yml` 里的 `dependency-hygiene` 作业，并删除 `scripts/check_node_modules_untracked.py` 与其单测 |
| 恢复 node_modules 的跟踪 | `git add -f chrome-extension/node_modules`（`.gitignore` 需同步移除该行）——**不建议**：会把 4.9 MB 依赖重新塞回索引，扫描面也重新被噪音淹没 |

**回滚后 CI 仍会绿**——门禁作业随文件一起撤掉，回到 `71c9eac` 的状态。
