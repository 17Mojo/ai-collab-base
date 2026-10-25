# RESULT-P1-EXTERNAL-USER-ONBOARDING-2026-10-25

**状态**: completed
**任务**: `TASK-P1-EXTERNAL-USER-ONBOARDING-001`（外部用户试用材料 + 走不通的产品断点修复）
**执行**: Claude Code（AGENT_EXEC）
**分支**: `feat/realmachine-coverage-expand`
**日期**: 2026-10-25

---

## 一句话结论

第 4 刀（W-D）按「材料先备好，等人」推进：**一页指南、3 问反馈模板、记录格式**三件材料已交付；
但为了让这份指南**不撒谎**，逐段走查外部用户的真实路径时挖出 **5 处走不通的断点**——
Pack 执行链路三段全断、AI 步骤广播到所有页面、popup 没有导入入口、
「导入 Pack」在装好的扩展里 404——**全部已修并加了测试与变异守护**。
**唯一还缺的是「人」**：真实发送链路至今没有任何一次真机记录（缺口 #5 仍开着）。

---

## 执行命令

以下 7 条即工单契约里的 `acceptance_commands`，逐字执行，全部通过：

### 1. `cd chrome-extension && node tests/run-tests.mjs`

```
ℹ tests 110
ℹ pass 110
ℹ fail 0
```

（本轮从 102 条增加到 110 条：新增 8 条扩展接线测试。）

### 2. `cd chrome-extension && node tests/adapter-matrix/adapter-test-runner.js`

```
  Total: 108/114 passed, 0 failed, 6 skipped
```

6 个 skip 是**诚实跳过**（既有的「需要真机登录态」项），不是失败。

### 3. `cd chrome-extension && node tests/real-machine/mutation-check.mjs`

```
全部 29 条变异都被杀死。
```

（本轮从 23 条增加到 29 条，新增 6 条：AI 步骤退回广播、后台不再传标签页、
popup 不再传标签页、popup 不再打开编辑器、构建不再复制嵌套布局、
把交付给外部用户的冒烟 Pack 的提示词改掉。）

### 4. `cd chrome-extension && npm run build`

```
=== Build Complete ===
Output directory: dist/
Load in Chrome: chrome://extensions → Developer mode → Load unpacked → select dist/
```

### 5. `python3 -m pytest tests/ -q`

```
3045 passed, 6 skipped in 39.59s
```

> 这条**第一次跑是红的**：`tests/e2e/test_integration.py` 里有一条静态断言
> 按**字面量**匹配源码 `".execute(message.packId"`，
> 而后台改成 async/await 写法后源码换行了 ⇒ 断言失配。
> 已把那条断言改成**忽略空白**的等价形式（意图不变：确认后台用 packId 调了执行器），
> 而不是把源码改回去迁就断言。

### 6. `python3 -m ruff check .`

```
All checks passed!
```

### 7. `python3 scripts/scan_secrets_pii.py --workspace .`

```
[OK] no secrets found
```

---

## 验证结果

### 交付物

| 文件 | 是什么 |
|---|---|
| `docs/EXTERNAL_USER_ONBOARDING.md` | 给外部人的**一页**指南：5 步 + 每步的成功标志 + 卡住了怎么办 + 已知限制 + 3 个问题 |
| `collaboration/results/external-user/README.md` | 记录格式说明（字段、判定口径、隐私红线） |
| `collaboration/results/external-user/TEMPLATE.md` | 空白记录模板 |
| `packs/examples/external-user-smoke.json` | 冒烟自检 Pack：一句提示词、零输入、AI 只需回一句话 |

### 走查外部用户真实路径时挖出并修掉的 5 处断点

| # | 断点 | 现象（外部用户看到的） | 修法 |
|---|---|---|---|
| 1 | popup 用不存在的 `pack.id` | 列表项 `data-id="undefined"`，点下去执行一个不存在的 Pack | 改用 `metadata.pack_id`（并兼容 `pack_id` / `id`） |
| 2 | 执行器从来没拿到过 Pack | 每次执行都报 `Pack not found: <id>` | 新增 `replacePacks()`，以 `chrome.storage.local["packs"]` 为事实源，启动时 / 每次执行前 / storage 变更时同步 |
| 3 | 内容脚本没有 `SEND_TO_AI` 分支 | Pack「执行成功」但产物是空的（AI 步骤拿到 `undefined` 仍算成功） | 补分支：注入文本 → 点发送 → 等回复 |
| 4 | AI 步骤用 `chrome.runtime.sendMessage` 广播 | 用户开 3 个 AI 页面时，提示词在 3 个页面里各发一次 | 已知目标标签页 ⇒ `chrome.tabs.sendMessage` 精确投递；不知才广播并标明是广播 |
| 5 | 外部用户**走不到导入 Pack 那一步** | popup 里没有导入入口；点设置页的「打开 Pack 编辑器」在**装好的扩展里 404** | popup 加「📥 导入 / 管理 Pack」按钮；静态资源复制收敛到 `static-assets.cjs` 一份，产物里保留扁平与 `public/` 嵌套两种布局 |

> 第 5 条是这次走查的直接产物：**说明书会写「在设置页打开 Pack 编辑器」，
> 而那个 URL 在装好的扩展里根本不存在**——不修就是给外部人一份假说明书。

### 测试结论

- **接线测试**（`tests/extension-wiring.test.mjs`，本轮新增）：18 条，覆盖
  消息类型双向对账、真的跑一次 `SEND_TO_AI`（jsdom 里跑**生产**内容脚本）、
  Pack 找得到、popup 渲染的 id、popup 传标签页、标签页定向、产物里页面真的存在、**交付给外部用户的那份冒烟 Pack 真的能跑起来**。
- **变异检查**：29 条全部被杀死，每条都要求**指定的那条**测试因此报错。
  其中 5 条是本轮新增的断点守护。
- **矩阵**：108/114（6 个既有 skip），生产 adapter 选择器没有回退。
- **未验证的部分**：以上全部是**模拟层**结论。真实发送链路（真机上点一下→真的发出去→把回复取回来）
  **仍然没有跑过一次**，见风险一节。

---

## 风险

| 风险 | 影响面 | 现状 |
|---|---|---|
| **真实发送链路仍未在真机上跑过**（缺口 #5） | 外部人第一次真机发送**很可能就是我们在抓 bug** | 指南里明写这一点，并给出「卡住了怎么办」对照表 |
| **千问的消息气泡/生成中信号只做了资产普查，未在真机验证**（缺口 #1b / #8） | 可能拿到半截回复，或永远等不到 | 指南不承诺「一定成功」，只给可观察的成功标志 |
| **Python 校验器与 JS 运行时的步骤类型口径不一致**（缺口 #9） | 按 Python 口径写的 Pack 在 JS 侧直接抛 `Unknown step type` | 已记入 `docs/REAL_MACHINE_REGRESSION.md` §6.2 #9，本次未改（属契约变更） |
| **`packs/examples/` 下 17 个示例 Pack 没有一个能过 Python 校验器**（缺口 #10） | 「照着示例写」这条路对使用者是断的 | 同上；本次只新增一个走 JS 运行时的自检 Pack |
| **`pack-storage-manager.js` 依赖尚不存在的后端**（缺口 #11） | 该模块的 Pack 管理路径不可用 | 当前可用路径是「storage 即事实源」；已记入 §6.2 |
| **真机只读探针（L1）没覆盖中文/英文两种界面** | 语言相关漂移未测 | 需要一次已登录 profile 的会话（第 2 刀 W-A） |

> 指南第 4 节「已知限制」把上面这些**原样**写给了外部用户——
> 说明书里不许出现「未验证」被说成「已通过」。

---

## 回滚

- 代码：本轮改动集中在 `chrome-extension/`（`src/background/pack-executor.js`、
  `src/background/service-worker.js`、`src/content/content-script.js`、`public/popup.*`、
  `vite.config.js`、`build.js`、新增 `static-assets.cjs`）与
  `tests/extension-wiring.test.mjs`、`tests/real-machine/mutation-check.mjs`。
  回滚 = `git revert` 本次提交；分支上已有 4b98bdc / 7ffdeb5 / fcaff14 / 71c9eac 可作参照。
- 文档：`docs/EXTERNAL_USER_ONBOARDING.md`、`collaboration/results/external-user/`、
  `docs/REAL_MACHINE_REGRESSION.md` 的 §6.1 / §6.2 / §7 / 附录 A。
- 记录：外部用户的试用记录**不随代码回滚**——它是事实记录，不因代码回滚而消失。
