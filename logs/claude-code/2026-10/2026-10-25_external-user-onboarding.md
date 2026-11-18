# 2026-10-25 · 外部用户试用材料（W-D：材料先备好，等人）

**工单**: `TASK-P1-EXTERNAL-USER-ONBOARDING-001`
**结果文件**: `collaboration/results/RESULT-P1-EXTERNAL-USER-ONBOARDING-2026-10-25.md`
**分支**: `feat/realmachine-coverage-expand`（PR #5）

---

## 做了什么

第 4 刀（W-D）按计划只做「材料先备好，等人」：
一页指南 + 3 问反馈模板 + 记录格式，外加一个让外部用户能真的跑起来的自检 Pack。

但**为了让指南不撒谎**，我按外部用户的真实路径走了一遍：

> 装扩展 → 打开 AI 网站 → 导入 Pack → 点 Pack → AI 回话

走完发现**这条路今天根本走不通**，一共 5 处断点：

1. popup 用不存在的 `pack.id` ⇒ 列表项 `data-id="undefined"`
2. 执行器从来没拿到过 Pack ⇒ 每次执行都是 `Pack not found`
3. 内容脚本没有 `SEND_TO_AI` 分支 ⇒ AI 步骤拿到 `undefined` 却被当成「成功」
4. AI 步骤广播 ⇒ 用户开 3 个 AI 页面就发 3 次
5. **外部用户连「导入 Pack」都走不到**：popup 没有导入入口；
   设置页打开 Pack 编辑器的 URL 在**装好的扩展里 404**（产物里只有扁平布局）

第 5 条是这次走查的直接产物——不修就是在给外部人一份**假说明书**。

## 关键判断

- **「等回复」这一步的判定条件**（`messageCount` 增长 + `isTyping()` 变 false）
  此前只有 L1 只读探针在管，真机上从没跑过。所以指南里**没有承诺「一定成功」**，
  只给了可观察的成功标志和「卡住了怎么办」对照表。
- **不能为了让指南好看而假装验证过**：指南第 4 节「已知限制」把
  缺口 #1b / #3 / #5 / #8 / #9 / #10 / #11 原样写给了外部用户。
- **「AI 步骤发到哪儿」以前没定义过**：广播是隐含行为。
  改成「已知目标标签页 ⇒ 精确投递；不知才广播并标明是广播」。

## 踩到的坑

- **e2e 静态断言按字面量匹配源码**：`tests/e2e/test_integration.py` 里
  `assert ".execute(message.packId" in content`——
  后台改成 async/await 写法后源码换行 ⇒ 断言失配 ⇒ **pytest 红**。
  修法是把断言改成**忽略空白**的等价形式（意图不变），
  而不是把源码改回去迁就断言。这条红是**上一轮改动带进来的**，
  本轮跑全量 pytest 才发现——说明「只跑扩展测试」是不够的。
- **静态资源复制逻辑有两份**（`build.js` 与 `vite.config.js`），
  两边各写各的文件清单 ⇒ 「产物里到底有哪些页面」没有唯一答案。
  收敛到 `static-assets.cjs` 一份，产物里保留扁平 + `public/` 嵌套两种布局。

## 验证

```
node tests/run-tests.mjs            → 110/110
node tests/adapter-matrix/...        → 108/114（6 skip，既有）
node tests/real-machine/mutation-check.mjs → 29/29 变异全被杀死
npm run build                        → 成功（dist/ 与 dist/public/ 两种布局）
python3 -m pytest tests/ -q          → 3045 passed, 6 skipped
python3 -m ruff check .              → All checks passed
scan_secrets_pii.py --workspace .    → [OK] no secrets found
```

CI（PR #5，2026-10-25）：14 个 job 全部 pass
（Bandit / Coverage Gate / mypy / chrome-extension-tests / fail-on-low-score /
health / lint / pack-validation / performance-tests / pip-audit /
python-tests 3.10+3.11+3.12 / secrets-scan）

## 后补的一条

材料交付后又补了一条守护：**用生产执行器跑那份交付给外部用户的 Pack**
（`packs/examples/external-user-smoke.json`）——问题在**交付物**里时，
模拟层任何测试都发现不了；配 1 条变异（改掉提示词）⇒ 29/29 全被杀死。

## 接下来等什么

- **等人**：第一个外部用户（材料齐了，缺的是人）。
- **等会话**：第 2 刀 W-A 的 L2 登录态会话（`/tmp/rm-profile` + `l2-send-observer.mjs`）。
  它是**唯一**能验证千问选择器「真机上命中」的办法；
  外部用户那一路也能部分替代，但**不能替代 L2 的证据形态**（截图 + 回执）。
