# RESULT-P1-REALMACHINE-REGRESSION-PREP-2026-10-25：真机回归准备 + 真机实测暴露的 adapter 漂移修复

- **状态**: completed
- **任务 ID**: TASK-P1-REALMACHINE-REGRESSION-PREP-001
- **change_id**: bugfix/no-spec
- **角色**: AGENT_EXEC（claude_code）
- **复核方**: AGENT_TEST（codearts_agent）
- **完成时间**: 2026-10-25T00:45+08:00

## 执行命令

```bash
# 1) 任务登记与状态流转
python3 -m ai_collab.cli tasks register --task-id TASK-P1-REALMACHINE-REGRESSION-PREP-001 ...

# 2) 契约验收命令（全部实跑，输出见下节）
cd chrome-extension && node tests/adapter-matrix/adapter-test-runner.js
cd chrome-extension && npm run build
python3 -m pytest tests/unit/test_real_machine_regression.py -q
python3 -m pytest tests/ -q
python3 -m ruff check .
python3 scripts/real_machine_regression.py list

# 3) 真机 L1 探针（只读，不注入文本、不点发送、不消耗额度）
cd chrome-extension && node tests/real-machine/dom-contract-probe.mjs \
  --locale=zh-CN --probe-send-button \
  --out=../collaboration/results/real-machine-runs/evidence/L1-2026-10-25-zh-CN.json
cd chrome-extension && node tests/real-machine/dom-contract-probe.mjs \
  --locale=en-US --probe-send-button \
  --out=../collaboration/results/real-machine-runs/evidence/L1-2026-10-25-en-US.json

# 4) 真机回归记录登记与对账
python3 scripts/real_machine_regression.py init --run-id RMR-2026-10-25-01 \
  --platforms chatgpt,claude,gemini --locales zh-CN,en-US --operator claude_code
python3 scripts/real_machine_regression.py record --run-id RMR-2026-10-25-01 \
  --layer L1 --platform gemini --status pass --locale zh-CN \
  --evidence "探针判定：生产 adapter 在真实 DOM 上找到输入框与发送按钮" \
  --evidence-file collaboration/results/real-machine-runs/evidence/L1-2026-10-25-zh-CN.json
python3 scripts/real_machine_regression.py record --run-id RMR-2026-10-25-01 \
  --layer L2 --platform gemini --status not-run --locale zh-CN \
  --reason "尚未执行：L2 需要已登录的真实账号 + 人工在浏览器里触发 Pack（真实发送、消耗额度）"
python3 scripts/real_machine_regression.py verify --run-id RMR-2026-10-25-01
```

### 改动落点

| 契约 | 落点 | 改动 |
|---|---|---|
| R1 查找函数去伪存真 | `chrome-extension/src/platforms/adapter-utils.js` | `findElement`/`findElements` 排除 `HTML`/`BODY` 页面根节点；`findElements` 全不匹配时返回**空集合**（删除「回退到页面全部 div」的旧行为——那行注释 `// fallback: empty NodeList` 此前是假的）；新增 `findVisibleElement`（祖先链上 `display:none`/`visibility:hidden|collapse`/`opacity:0` 即不算命中；**不用** `getBoundingClientRect`，jsdom 无布局、rect 恒为 0×0） |
| R2 10 个 adapter 统一口径 | `chrome-extension/src/platforms/*-adapter.js`（10 个） | `getMessageList()` 统一走 `findElements(this.selectors.messageList)`（此前有三套实现：①`findElements` ②按下标取 `[0]`/`[1]`——让 `messageList[2]`/`[3]` 成为**死代码** ③内联循环 + div 回退）；`isTyping()` 的停止按钮与打字指示器**都**做可见性判定；`getChatInput()`/`getSendButton()` 改用 `this.selectors.*` |
| R3 Gemini 选择器修复 | `chrome-extension/src/platforms/gemini-adapter.js` | `sendButton` 补类名选择器（两种语言都命中）与中文 `aria-label`；`messageList`/`typingIndicator`/`stopButton` 按真机形状补齐 |
| R4 模拟层改造 | `chrome-extension/tests/adapter-matrix/{adapter-test-runner.js,adapter-test-utils.js,fixtures/*.html}` | 矩阵**不再手抄** `SELECTORS`，改为 `import()` 生产 adapter 模块；fixture 改成「真实站点 DOM 快照 + `data-role` 标注契约」；新增 6 条守护用例（详见下节） |
| R5 CI 变硬 | `.github/workflows/test.yml`（仅 `chrome-extension-tests` job） | 改跑真实矩阵，删除 `|| echo "... skipped"` 掩码；`npm ci` 不再用 `|| npm install` 兜底；追加 `npm run build` 作为门禁 |
| R6 真机探针 | `chrome-extension/tests/real-machine/dom-contract-probe.mjs`（新建） | esbuild 打包**生产** adapter → 注入真实站点 → 调真实方法；默认只读；区分「没找到输入框」与「登录墙/拦截」；支持 `--locale=` |
| R7 手册与记录器 | `docs/REAL_MACHINE_REGRESSION.md`（新建）、`scripts/real_machine_regression.py`（新建） | 见下节 |
| R8 记录器诚实性规则 | 同上 + `tests/unit/test_real_machine_regression.py`（新建） | 8 条可机检规则，逐条有单测守护 |
| ESM 化 | `chrome-extension/src/package.json`、`chrome-extension/tests/adapter-matrix/package.json`（新建） | 显式声明 `"type": "module"`，让 Node 的 `import()` **确定性地**把 `src/**/*.js` 当 ES 模块（否则依赖 Node 的语法嗅探） |

## 验证结果

### 1. 验收命令全绿（真实输出）

| 命令 | 真实输出 | 结果 |
|---|---|---|
| `cd chrome-extension && node tests/adapter-matrix/adapter-test-runner.js` | `Total: 110/114 passed, 0 failed, 4 skipped`（退出码 0） | ✅ |
| `cd chrome-extension && npm run build` | `=== Build Complete ===`（content-script 17.82 kB / service-worker 92.58 kB，退出码 0） | ✅ |
| `python3 -m pytest tests/unit/test_real_machine_regression.py -q` | `18 passed in 0.11s` | ✅ |
| `python3 -m pytest tests/ -q` | `3037 passed, 6 skipped in 42.70s`（0 failed） | ✅ |
| `python3 -m ruff check .` | `All checks passed!` | ✅ |
| `python3 scripts/real_machine_regression.py list` | `✅ RMR-2026-10-25-01: partial（9 条记录）` | ✅ |

6 条 skipped 全部是环境依赖型（缺 backend db 1 条 + 需 `127.0.0.1:8000` 在线 5 条），与本工单无关。

矩阵的 4 条 skipped 是**如实标记**的：部分平台的 `messageList` 只有 2 个选择器，
「第 3 个及以后的选择器也能生效」这条路径**不存在**，用例返回 `SKIP` 而不是假装通过。

### 2. 真机 L1 实测（本轮，含修复前对照）

**修复前**（同一任务前半段的实测，2026-10-25）：Gemini 的 `sendButtonVerdict` 为
`adapter_drift`——页面上**有**发送按钮，生产 adapter **一个都没命中**；
`messageCount` 为 **104**（「回退到页面全部 div」的旧行为在真机上的真实后果）。

**修复后**（本轮实测，两个界面语言各跑一次）：

| 界面语言 | 平台 | 探针结论 | 发送按钮命中情况 |
|---|---|---|---|
| zh-CN | Gemini | `pass` | 找到 `<button>` aria=`发送`（命中 `gem-icon-button.send-button button` / `.send-button button` / `button[aria-label="发送"]`） |
| zh-CN | ChatGPT | `bot_check`（HTTP 403） | 未验证——需要已登录 profile |
| zh-CN | Claude.ai | `bot_check`（HTTP 403） | 未验证——需要已登录 profile |
| en-US | Gemini | `pass` | 找到 `<button>` aria=`Send message`（命中 4 条选择器） |
| en-US | ChatGPT / Claude.ai | `bot_check`（HTTP 403） | 未验证——需要已登录 profile |

两次探针的 `verdict` 均为 `partially-unverified`、`failed=0`。

**关键发现（缺陷是语言相关的）**：旧选择器 `button[aria-label*="Send"]` 在英文界面
**侥幸命中**（英文 aria-label 是 `Send message`），在中文界面**一个都命中不了**
（中文 aria-label 是 `发送`）。只跑默认语言就看不见这类漂移——这正是缺陷长期潜伏
的原因。修复后两个语言都靠类名选择器命中。

**修复后 `messageCount` 从 104 降到 0**（零状态页面上本就没有消息气泡，
104 全是「回退到页面全部 div」带来的噪声），真机复验确认旧行为已消失。

### 3. 模拟层现在具备「发现漂移」的能力（变异验证）

只跑绿是**不够**的——每条守护用例都必须证明「把被守护的缺陷改回去，它会变红」。
本轮逐条做了变异（每次只改一处，跑完立刻从备份恢复该文件）：

| 变异 | 注入的缺陷 | 矩阵的反应 | 结果 |
|---|---|---|---|
| M1 | Gemini `sendButton` 退回漂移前的旧选择器集合 | `getSendButton() 返回 null` | ✅ 抓得住 |
| M2 | `findElement` 不再排除页面根节点 | `findElement() 返回了页面根节点 <body>` | ✅ 抓得住 |
| M3 | `findElements` 恢复「全不匹配就回退到页面全部 div」 | `期望空集合，实际返回 9 个元素` | ✅ 抓得住 |
| M4 | Gemini `isTyping()` 的打字指示器不做可见性判定 | `isTyping() 返回 true` | ✅ 抓得住 |
| M5 | 千问 `getMessageList()` 只取第 1 个选择器 | `第 3 个及以后的选择器（.response-content）没有生效` | ✅ 抓得住 |
| M6 | 矩阵漏掉一个生产 adapter（chatglm） | `生产新增了 adapter 但矩阵没覆盖：chatglm-adapter.js` | ✅ 抓得住 |

6/6 全部被抓。变异跑完后工作区逐文件还原，矩阵复跑仍是 `110/114 passed, 0 failed`。

### 4. 记录器的诚实性规则（逐条实测）

记录器 `scripts/real_machine_regression.py` 把「没跑」和「跑过」在机器层面区分开。
本轮用**真实证据文件**跑通并反向验证：

| 场景 | 实测行为 | 结果 |
|---|---|---|
| 正常登记（L1 Gemini 两个语言 pass + 证据文件） | `verify` → 结论 `partial`、一致性 ✅、退出码 **2**（一致但没跑完） | ✅ |
| 把未验证写成通过（把 `bot_check` 的证据挂到一条 `pass` 记录上） | `verify` → `证据与结论不符——探针判定 outcome=bot_check，记录却写 pass`，退出码 **1** | ✅ 抓得住 |
| `pass` 但不挂证据文件 | `verify` → `pass 必须有 evidence_file` | ✅ 抓得住 |
| 证据文件路径不存在 | `verify` → `证据文件不存在：…` | ✅ 抓得住 |
| L2 记 `pass` 而 L1 没记 `pass` | `verify` → `L2 记为 pass，但 L1 没有 pass 的记录` | ✅ 抓得住 |
| 平台缺 L1 或缺 L2 条目 | `verify` → `缺 L1 记录` / `缺 L2 记录` | ✅ 抓得住 |
| `list` 遇到同目录下的探针证据 JSON | 跳过并提示「跳过 1 个非记录文件」，不再误报成一条坏记录 | ✅ |

单测 18 条覆盖上述全部规则。

**路线门禁恒开**：`verify` 每次都打印「本记录只覆盖 L1/L2 证据，不含『第一个外部用户』
——门禁仍为开启状态，不得据此拍板路线」。本轮记录 `RMR-2026-10-25-01` 的结论是
`partial`，**没有**、也**不可能**被判为 `passed`。

### 5. CI 假绿的处置

`.github/workflows/test.yml` 的 `chrome-extension-tests` job 此前是：

```bash
node tests/test-adapters.js 2>/dev/null || echo "adapter tests skipped"
node tests/test-branch-executor.js 2>/dev/null || echo "branch tests skipped"
```

那两个文件**早已归档**到 `chrome-extension/tests/_archive/`——命令必然失败、
必然走 `echo` 分支，于是**扩展测试一个都没跑**，CI 长期绿灯。
现在改跑真实矩阵（失败即红），并追加 `npm run build` 作为构建门禁。

## 测试结论

| 契约条款 | 结论 | 证据 |
|---|---|---|
| R1 查找函数去伪存真 | ✅ 通过 | 变异 M2/M3 均被矩阵抓红；真机上 `messageCount` 从 104 降到 0 |
| R2 10 个 adapter 统一口径 | ✅ 通过 | 变异 M4/M5 被抓红；矩阵 10 个平台全绿 |
| R3 Gemini 选择器修复 | ✅ 通过 | 变异 M1 被抓红；真机 zh-CN / en-US 两个语言均命中发送按钮 |
| R4 模拟层跑生产源码 | ✅ 通过 | 变异 M6 被抓红；矩阵 110/114 passed、0 failed、4 skipped（skipped 为如实标记） |
| R5 CI 变硬 | ✅ 通过 | workflow 中已无 `\|\| echo "... skipped"` 掩码；`npm ci` 无兜底 |
| R6 真机探针 | ✅ 通过 | 两个语言各跑一次，产出可机检的 JSON 证据；结论区分 pass / 未验证 / 失败 |
| R7 手册与记录器 | ✅ 通过 | `docs/REAL_MACHINE_REGRESSION.md` 7 节齐全；记录器 4 个子命令实跑通过 |
| R8 诚实性规则 | ✅ 通过 | 8 条规则逐条实测 + 18 条单测 |
| 验收命令 | ✅ 通过 | 6 条全绿（含全量 pytest 3037 passed / 0 failed） |

**整体结论：契约 R1–R8 全部满足，6 条验收命令全绿，全量测试无回归，
6/6 变异全部被矩阵抓红。**

## 已知缺口（如实记录，未修复）

| # | 缺口 | 影响 |
|---|---|---|
| 1 | Gemini 的 `messageList` / `messageContent` 选择器**未在真机验证** | Gemini 的「等回复 + 取内容」链路仍是未验证状态（未登录的零状态页面上没有消息气泡可测） |
| 2 | Gemini 真实**停止生成按钮**的 `aria-label` 未验证 | `isTyping()` 的停止按钮分支在 Gemini 上未验证（需登录后真实发起一次生成） |
| 3 | 千问的 `messageList` 用了 `[class*="message"]` 这类**宽松选择器** | 可能多计消息数、影响响应等待；矩阵只把它标成「偏松」，没有断言其正确 |
| 4 | **只有 Gemini 的 fixture 是真实 DOM 快照**，其余 9 个仍是手写 mock | 其余 9 家一旦改版，矩阵同样可能假绿 |
| 5 | ChatGPT / Claude.ai 在**无登录态**下 L1 未验证（实测 HTTP 403） | 这两家的 DOM 契约目前**没有** L1 结论 |
| 6 | 探针只覆盖 **3 个**平台，矩阵覆盖 10 个 | 其余 7 家的真机回归还没做 |
| 7 | 10 个平台里**只有 3 家**在真机上验证过 | 「矩阵 110/114 全绿」不等于「10 家都能用」 |

## 风险

1. **L1 全绿 ≠ 能用**：本轮 L1 只证明了「生产 adapter 在真实 DOM 上还能找到输入框与
   发送按钮」。发送之后的**等待回复、取回内容**这条链路在 Gemini 上**未验证**（缺口 #1/#2）。
2. **fixture 快照只有 1/10 是真的**（缺口 #4）：其余 9 个平台的矩阵仍然是「对着手写 mock
   跑生产代码」——比改前好（不再有副本漂移），但**不等于**对着真实站点跑。
3. **CI 变硬可能暴露既有失败**：`npm ci` 不再有 `|| npm install` 兜底，`npm run build`
   也进了门禁。本地实跑两者均通过；但 CI runner 的 Node 版本（20）与本机（23）不同，
   首次跑可能暴露环境差异导致的红。**这是把假绿灯变真门禁的代价，不是引入新缺陷。**
4. **`chrome-extension/node_modules/` 仍在 git 跟踪中**（219 个文件，`.gitignore` 的规则
   对已跟踪文件无效）。`npm ci` 会先删掉整个 `node_modules` 再重装，CI 里不会因此失败，
   但本仓的仓库体积与密钥扫描面都受它影响（扫描器已加目录排除）。**本工单未动它**——
   清理它属于独立的技术债工单，不应混进这次缺陷修复。
5. **真机探针依赖外部站点可达**：站点改版、网络波动、区域性限制都会让 L1 出现未验证。
   探针把这类情况单列为 `login_wall`/`bot_check`（**不计失败**），但它们也**不构成**通过。
6. **L2 完全未执行**：本轮三个平台的 L2 都是 `not-run`（需已登录账号 + 人工触发）。
   记录器把这种情况判为「一致但没跑完」（退出码 2），**不允许**被当成完成。
7. **路线 A/B 决策门禁仍未关闭**：「第一个外部用户」这一环**不在**本工单范围内，
   也不在任何脚本的证据范围内。本工单的产出只把「真机 3 平台回归」这半段准备好了。

## 回滚

```bash
# 1) 撤回生产代码与 CI 改动
git checkout -- .github/workflows/test.yml \
  chrome-extension/src/content/content-script.js \
  chrome-extension/src/platforms/

# 2) 删除本工单新建的文件
rm -f chrome-extension/src/package.json
rm -f chrome-extension/tests/adapter-matrix/package.json
rm -rf chrome-extension/tests/real-machine/
rm -f docs/REAL_MACHINE_REGRESSION.md
rm -f scripts/real_machine_regression.py
rm -f tests/unit/test_real_machine_regression.py
rm -f collaboration/tasks/TASK-P1-REALMACHINE-REGRESSION-PREP-001.md
rm -f collaboration/results/RESULT-P1-REALMACHINE-REGRESSION-PREP-2026-10-25.md
rm -rf collaboration/results/real-machine-runs/

# 3) 撤回矩阵与 fixture 的改动
git checkout -- chrome-extension/tests/adapter-matrix/

# 4) 任务状态回退
python3 -m ai_collab.cli tasks update --task-id TASK-P1-REALMACHINE-REGRESSION-PREP-001 \
  --status cancelled --reason "按回滚说明撤回"
```

回滚后，Gemini 的中文界面发送按钮缺陷会**重新出现**（矩阵也会随之回到「测副本」
的老形态、CI 恢复假绿灯）。回滚**不触碰** `ai_collab/`、`openspec/`、`packs/`、`config/`、
`memory/` 下任何文件。
