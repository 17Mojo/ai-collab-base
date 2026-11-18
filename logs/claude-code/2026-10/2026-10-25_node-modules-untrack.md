# 2026-10-25 node_modules 取消跟踪 + 依赖入库状态门禁

**任务**: `TASK-P1-NODE-MODULES-UNTRACK-001`
**执行**: Claude Code（AGENT_EXEC）
**分支**: `chore/untrack-node-modules`（基线 `main` @ `71c9eac`）
**worktree**: `/tmp/rm-c1`（独立于主工作区）

---

## 为什么单独做

用户在批准执行顺序时明确要求：
「C-1（node_modules）**必须独立成工单，不与缺陷修复混在一起**」。

做法：独立分支 + 独立 worktree（`git worktree add /tmp/rm-c1`）。
主工作区一个 `node_modules` 字都没动，两个 PR 各自独立评审与合并。

## 现状是个「以为做了、其实没做」的状态

```bash
$ grep node_modules .gitignore
chrome-extension/node_modules/        # 第 121 行，早就列了

$ git ls-files chrome-extension/node_modules | wc -l
129                                  # 但文件还在索引里
```

`.gitignore` **只影响未跟踪文件**。已跟踪的文件不会因为加进 ignore 就消失——
所以「.gitignore 里明明写了」和「真的没入库」是两件事。

## 两条不变量（缺一不可）

| | 不变量 | 少了它 |
|---|---|---|
| A | `node_modules/` 下的文件不得被跟踪 | 仓库虚胖、扫描器被噪音淹没 |
| B | 锁文件必须在库 | `npm ci` 无法复现依赖版本 |

> **只做 A 不做 B 等于把真问题用假象掩盖**。仓库小了是假象，
> 「CI 每次装出来的依赖可能不同」才是真问题——后者不解决，
> 光把 node_modules 挪出去只是把问题藏到了别处。
> 所以门禁脚本两条一起查。

## 实测收益（不夸大）

| 指标 | 之前 | 之后 |
|---|---|---|
| 被跟踪的 node_modules 文件 | 129 个 / 4.9 MB | 0 个 |
| 工作区检出的内容 | 16.0 MB | **11.1 MB（-31%）** |
| `.git` 历史体积 | 16 MB（size-pack 2.94 MiB） | **16 MB（不变）** |

**`.git` 不会因为这个提交而变小**——取消跟踪只改索引，历史里的 blob 仍在。
要真正瘦身得 `git filter-repo` 重写历史，**不做**：
改写所有 commit id、影响所有协作者的分支、还会让「历史里曾有过这份拷贝」
这个事实消失。代价远大于收益。

**也不夸大扫描器的收益**：237 → 0 是 2026-10-24 那个体检工单做的。
本工单只是让扫描面里彻底没有依赖产物，是锦上添花，不是修 bug。

## 门禁脚本的两个边界

单测里钉住了容易写错的两处：

- `src/node_modules_helper.js`——名字里带 `node_modules` 但**不是目录**，不算违规；
- `tests/playwright/node_modules/...`——嵌套目录，同样会被挑出来。

判据是路径里有 `node_modules/` **这个目录段**，不是简单的子串匹配。

## 端到端验证

12 条单测里有两条是**真的造仓库**：
`git init` → `git add -f .`（含 node_modules）→ 门禁必须返回 1；
只 add 锁文件 → 门禁必须返回 0。

门禁在真实仓库上的表现也实测过：取消跟踪前它会拦下（129 个文件），
取消跟踪后报 `[OK]`。**不是写完就没再验证过。**

## CI 接线的一个小讲究

`dependency-hygiene` 作业**不装任何依赖**——脚本只用标准库
（`subprocess` + `pathlib`）。所以它不受 `npm ci` 成功与否影响，
也不会因为网络问题误报。放在 `lint.yml` 而不是 `test.yml`，
因为它跟「代码质量」是同一类：仓库状态卫生。

## 验证结果

- 门禁脚本单测 `12/12`；Python 全量 `3048 passed / 7 skipped / 0 failed`
  （比主工作区多 1 个 skip：worktree 是全新检出，不含 gitignore 掉的本地产物）
- ruff `All checks passed!`；密钥扫描 `0 命中`
- 门禁实测：取消跟踪后 `[OK] 依赖入库状态合规：648 个被跟踪文件中 0 个落在 node_modules 下`

## 留给下一轮的事

1. **`.git` 历史体积没变**（16 MB）——要瘦身得重写历史，本工单明确不做；
2. 协作者拉取本分支后 `node_modules` 仍在（`--cached` 不删工作区），
   本地若已删则 `npm ci` 即可（锁文件在库）；
3. 主工作区里 `chrome-extension/node_modules/.package-lock.json` 有一个
   **本工单之外**的未提交改动（会话开始前就存在）——按共享工作区规则
   只提交自己的文件，**未纳入本工单**。
