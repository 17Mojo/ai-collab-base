---
task_id: TASK-P1-REALMACHINE-REGRESSION-PREP-001
change_id: bugfix/no-spec
status: pending
priority: P1
assignee: claude_code
assignee_role: AGENT_EXEC
reviewer: codearts_agent
primary_skill: api-test-pro
support_skills:
  - testing
  - documentation
created_at: 2026-10-25T00:30:00+08:00
acceptance_commands:
  - "cd chrome-extension && node tests/adapter-matrix/adapter-test-runner.js"
  - "cd chrome-extension && npm run build"
  - "python3 -m pytest tests/unit/test_real_machine_regression.py -q"
  - "python3 -m pytest tests/ -q"
  - "python3 -m ruff check ."
  - "python3 scripts/real_machine_regression.py list"
result_file: collaboration/results/RESULT-P1-REALMACHINE-REGRESSION-PREP-2026-10-25.md
---

# TASK-P1-REALMACHINE-REGRESSION-PREP-001：真机回归准备（探针 / 手册 / 记录器）+ 真机实测暴露的 adapter 漂移修复

> **来源**：PR #2 合并并归档 OpenSpec 变更（`2026-10-24-add-concurrent-workspace-guard`）后，
> 路线 A/B 决策门禁（`memory/project_route_decision.md`）剩下的唯一真证是
> 「真机 3 平台回归 + 第一个外部用户」。本工单做**前半段的准备**，
> 并修掉准备过程中真机实测抓出的**产品缺陷**。
>
> **本工单不含**「第一个外部用户」——那需要外部人，不是内部再跑一遍自动化。

## 一、真机实测抓到的产品缺陷（2026-10-25）

Gemini 的生产 `sendButton` 选择器在**真实站点上一个都命中不了**（中文界面）。
两种界面语言各实测一次：

| 界面语言 | 发送按钮内层 `<button>` 的 aria-label | 旧选择器 `button[aria-label*="Send"]` |
|---|---|---|
| zh-CN | `发送` | **0 命中** |
| en-US | `Send message` | 1 命中（**侥幸**——英文界面下掩盖了缺陷） |

**而当时的模拟层测试是全绿的。** 绿灯与真实行为背离，根因是三处结构性缺陷：

| 编号 | 缺陷 | 位置 | 后果 |
|---|---|---|---|
| F3 | 生产 `sendButton` 选择器漂移 | `src/platforms/gemini-adapter.js` | 中文界面下 Gemini 的 Pack **完全无法发送** |
| F4 | 模拟层手抄了一份 `SELECTORS` 表 | `tests/adapter-matrix/adapter-test-runner.js` | 生产选择器漂移了，矩阵**照样全绿**（结构上无法发现漂移） |
| F5 | `findElements` 全不匹配时回退到「页面全部 div」；`findElement` 会把 `<body>` 当合法命中 | `src/platforms/adapter-utils.js` | 消息计数虚高（真机实测 104）；Gemini 的 `<body>` 常驻 `enable-lm-loading-animation`，`[class*="loading"]` 必然命中它 → `isTyping()` 恒为 true → 响应等待必然超时 |

附带发现并修掉两处：

- `isTyping()` 的**打字指示器**在真实站点空闲态是**常驻 DOM 但 `display:none`**——
  「元素存在」不等于「正在打字」，必须做可见性判定（`display`/`visibility`/`opacity` 走祖先链）。
- **CI 假绿**：`.github/workflows/test.yml` 里
  `node tests/test-adapters.js 2>/dev/null || echo "adapter tests skipped"`——
  那两个文件早已归档到 `tests/_archive/`，命令必然失败、必然走 `echo` 分支，
  **CI 长期绿灯，扩展测试一个都没跑**。

## 二、目标

1. 把 F3/F4/F5 修掉，并让**模拟层具备发现漂移的能力**（矩阵直接跑生产 adapter 源码）。
2. 提供 **L1 真机只读探针**：把生产 adapter 打进真实站点页面，产出可机检的证据。
3. 提供 **L2 人工真实发送的操作手册**（`docs/REAL_MACHINE_REGRESSION.md`）。
4. 提供**记录与对账工具**（`scripts/real_machine_regression.py`），把「没跑」和「跑过」
   在机器层面区分开。
5. **CI 变硬**：扩展测试真正跑起来，失败即红。

## 三、契约

### R1 `src/platforms/adapter-utils.js`：查找函数去伪存真

- `findElement` / `findElements` **排除页面根节点**（`HTML`/`BODY`）。
- `findElements` 全不匹配时返回**空集合**（不再回退到「页面全部 div」）——
  注释里那句 `// fallback: empty NodeList` 之前是**假的**。
- 新增 `findVisibleElement(selectors)`：命中元素**及其祖先链**上
  `display:none` / `visibility:hidden|collapse` / `opacity:0` 时不算命中。
  可见性判定**不用** `getBoundingClientRect`——jsdom 无布局，rect 恒为 0×0。

### R2 10 个 adapter：`getMessageList()` / `isTyping()` 统一口径

- `getMessageList()` 统一走 `findElements(this.selectors.messageList)`。
  历史实现有三套：①`findElements`（chatgpt/claude/gemini）
  ②按下标取 `[0]`/`[1]`（kimi/longcat/qianwen/yiyan/yuanbao/chatglm——
  这让 `messageList[2]`/`[3]` **成为死代码**）③内联循环 + div 回退（deepseek）。
- `isTyping()` 的停止按钮与打字指示器**都**走 `findVisibleElement`。
- 9 个 adapter 的 `getChatInput()` / `getSendButton()` 改用 `this.selectors.*`，
  与模块导出的 `SELECTORS` 保持同一份对象。

### R3 `src/platforms/gemini-adapter.js`：选择器修复（F3）

- `sendButton` 补类名选择器（两种语言都命中）与 `button[aria-label="发送"]`，
  保留旧选择器兼容历史 DOM。
- `messageList` / `typingIndicator` / `stopButton` 同步按真机形状补齐。

### R4 模拟层改造（F4）：矩阵必须跑**生产源码**

- 矩阵**不再手抄** `SELECTORS`；改为 `import()` 生产 adapter 模块。
- fixture 从「假 DOM」改成「**真实站点 DOM 快照**」+ `data-role` 标注契约
  （`chat-input` / `send-button` / `message`）。
- 新增守护用例：第 3 个及以后的选择器生效、`getMessageList()` 不越界、
  `isTyping()` 空闲态为 false、`adapter.selectors` 与模块 `SELECTORS` 同一份、
  矩阵覆盖 `src/platforms` 下全部 adapter、工具层三条（不把 `<body>` 当命中、
  全不匹配返回空集合）。

### R5 CI 变硬

- `.github/workflows/test.yml` 的 `chrome-extension-tests` 改跑真实矩阵，
  **去掉** `|| echo "... skipped"` 掩码；`npm ci` 不再用 `|| npm install` 兜底。
- 追加 `npm run build` 作为门禁（矩阵绿不代表能构建）。

### R6 真机探针（L1）

- `chrome-extension/tests/real-machine/dom-contract-probe.mjs`：
  esbuild 打包**生产** adapter → 注入真实站点 → 调真实方法；
  **默认只读**（不注入文本、不点发送、不消耗额度）。
- 必须区分「没找到输入框」与「撞登录墙 / 人机校验」——后者**不计失败**，
  但也**不构成**通过（记 `unverified`）。
- 必须支持 `--locale=`：漂移随界面语言变化，**两个语言都要跑**。

### R7 手册与记录器

- `docs/REAL_MACHINE_REGRESSION.md`：L1 / L2 定义、前置条件、逐步操作、
  证据要求、判据、**已知缺口清单**、与路线门禁的关系。
- `scripts/real_machine_regression.py`：`init` / `record` / `verify` / `list`；
  规则见 R8。

### R8 记录器的诚实性规则（可机检）

| 规则 | 判为不一致的条件 |
|---|---|
| `pass` 必须有证据 | 缺 `evidence` 或缺 `evidence_file` |
| 证据文件必须存在 | 路径指向不存在的文件 |
| 证据与结论必须一致 | 探针 JSON 写着 `login_wall`，记录却写 `pass` |
| 没跑要写原因 | `unverified` / `not-run` 缺 `reason` |
| L1 必须带语言 | 缺 `locale` |
| 平台覆盖 | 缺 L1 或缺 L2 条目 |
| L1 与 L2 不可互替 | L2 记 `pass` 而同平台 L1 不是 `pass` |
| **路线门禁恒开** | 记录**永远**不构成「第一个外部用户」证据 |

### R9 范围限制

| 允许修改 | 禁止修改 |
|---|---|
| `chrome-extension/src/platforms/*.js` | `ai_collab/` 下任何文件 |
| `chrome-extension/src/content/content-script.js` | `openspec/` 下任何文件（变更已归档） |
| `chrome-extension/tests/**` | `packs/**`、`config/**` |
| `chrome-extension/package.json` 之外的包元数据新增（`src/package.json`、矩阵 `package.json`） | `chrome-extension/package-lock.json`（已入库且无需改动） |
| `.github/workflows/test.yml`（仅 `chrome-extension-tests` 这一 job） | `.github/workflows/` 下其他 workflow |
| `docs/REAL_MACHINE_REGRESSION.md`（新建） | `docs/` 下既有文档 |
| `scripts/real_machine_regression.py`（新建） | `scripts/` 下既有脚本 |
| `tests/unit/test_real_machine_regression.py`（新建） | `tests/` 下既有测试 |
| `collaboration/tasks/`、`collaboration/results/`、`logs/claude-code/` | `memory/`（只读镜像，由 `scripts/sync_agent_memory.py` 生成） |

## 四、验收标准

- [ ] 矩阵全绿，且**每条守护用例都做过变异验证**（把被守护的缺陷改回去，矩阵必须变红）
- [ ] 真机探针在 zh-CN / en-US 两个语言下都跑过，结论写进结果文件
- [ ] CI 不再有 `|| echo "... skipped"` 掩码
- [ ] 记录器的每条诚实性规则都有单测守护
- [ ] 结果文件含「执行命令 / 验证结果 / 测试结论 / 风险 / 回滚」各段
- [ ] 结果文件头部的 `- **状态**: completed` 在前 40 行内

## 五、参考

- 结果文件：`collaboration/results/RESULT-P1-REALMACHINE-REGRESSION-PREP-2026-10-25.md`
- 手册：`docs/REAL_MACHINE_REGRESSION.md`
- 记录器：`scripts/real_machine_regression.py`
- 探针：`chrome-extension/tests/real-machine/dom-contract-probe.mjs`
- 路线门禁背景：`memory/project_route_decision.md`
- 协议：`collaboration/PROTOCOL.md`（§7.3 收口要求、§7.4 结果文件四段契约）
