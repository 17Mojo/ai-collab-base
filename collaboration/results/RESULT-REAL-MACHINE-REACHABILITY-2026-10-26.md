# RESULT-REAL-MACHINE-REACHABILITY-2026-10-26

- **状态**: completed
- **任务**: 真机回归第 1 刀 · B-1「探针扩 10 平台（先出可达性体检表）」
- **执行**: Claude Code（AGENT_EXEC）
- **分支**: `feat/realmachine-coverage-expand`　**PR**: [#5](https://github.com/17Mojo/ai-collab-base/pull/5)
- **日期**: 2026-10-26
- **运行记录**: [`collaboration/results/real-machine-runs/RMR-2026-10-26-01.json`](real-machine-runs/RMR-2026-10-26-01.json)
- **证据文件**: [`evidence/L1-2026-10-26-zh-CN.json`](real-machine-runs/evidence/L1-2026-10-26-zh-CN.json) · [`evidence/L1-2026-10-26-en-US.json`](real-machine-runs/evidence/L1-2026-10-26-en-US.json)

---

## 一句话结论

十平台 × 双语言的 L1 只读体检跑完：**7 家通过、3 家未验证（登录墙/人机校验，不计失败）、0 家失败**。

这一轮真正有价值的产出不是「几家通过」，而是三条**会改变后续计划**的实测结论：

1. **千问不认 `Accept-Language`** —— en-US 那轮拿到的仍然是中文界面（发送按钮
   `aria=发送消息`，与 zh-CN **逐字相同**）。所以「千问 × 2 语言」跑的是同一个 DOM，
   等于同一轮跑两遍，**零信息量**。原定的第 1 轮覆盖口径据此调整。
2. **Gemini 认** —— 同一个站点，zh-CN 的发送按钮是 `aria=发送`、en-US 是
   `aria=Send message`，**生产 adapter 命中的选择器也跟着换**
   （`aria-label*="Gemini"` → `aria-label*="prompt"`）。语言维度必须落在 Gemini 上，
   才是真的在验「多语言 DOM 契约」。
3. **发送按钮子探针有两类输出不是结论** —— 「探测不可用」和「未发现发送按钮类元素」
   都**不能**读成产品缺陷：前者是探针自己的通用选择器太窄（Kimi）或点击预算被慢
   页面吃掉（zh-CN 的 Yuanbao/ChatGLM 加载 31s → `click` 超时；同一份代码在 en-US
   加载 3.3s 时给出了结论），后者只说明**站点的形状与探针的选择器对不上**，要人工确认。

---

## 执行命令

```bash
# 1) 中文界面，十平台，只读探针（真实 Chrome，匿名首屏）
cd chrome-extension
node tests/real-machine/dom-contract-probe.mjs --channel=chrome --locale=zh-CN \
     --probe-send-button --out=/tmp/l1-sweep-zh.json

# 2) 英文界面，同一套代码
node tests/real-machine/dom-contract-probe.mjs --channel=chrome --locale=en-US \
     --probe-send-button --out=/tmp/l1-sweep-en.json

# 3) 证据落进仓库
cp /tmp/l1-sweep-zh.json ../collaboration/results/real-machine-runs/evidence/L1-2026-10-26-zh-CN.json
cp /tmp/l1-sweep-en.json ../collaboration/results/real-machine-runs/evidence/L1-2026-10-26-en-US.json

# 4) 建一条 run 记录并逐条登记（10 平台 × 2 语言 = 20 条 L1）
cd ..
python3 scripts/real_machine_regression.py init --run-id RMR-2026-10-26-01 \
  --platforms chatgpt,claude,gemini,deepseek,kimi,longcat,qianwen,yiyan,yuanbao,chatglm \
  --locales zh-CN,en-US --operator claude_code --purpose "..."
# …每条一次 record（outcome=pass→pass；bot_check/login_wall→unverified+reason）

# 5) 对账
python3 scripts/real_machine_regression.py verify --run-id RMR-2026-10-26-01
```

---

## 验证结果

### 可达性体检表（L1，只读，匿名首屏，真实 Chrome）

| # | 平台 | zh-CN | en-US | 命中的输入框选择器 | 发送按钮子探针 |
|---|------|-------|-------|--------------------|------------------|
| 1 | ChatGPT | `bot_check`（HTTP 403） | `bot_check` | — | 未验证 |
| 2 | Claude.ai | `bot_check`（HTTP 403） | `bot_check` | — | 未验证 |
| 3 | Gemini | ✅ pass 7998ms | ✅ pass 4178ms | zh: `contenteditable[aria-label*="Gemini"]`｜`.ql-editor`｜`[role=textbox]`<br>en: `contenteditable[aria-label*="prompt"]`｜`aria-label*="Gemini"`｜… | ✅ zh `aria=发送` / en `aria=Send message` |
| 4 | DeepSeek | `login_wall` | `login_wall` | — | 未验证 |
| 5 | Kimi AI | ✅ pass 808ms | ✅ pass 775ms | `div.chat-input-editor` | ⚠️ 探测不可用（`no-input-element`）——**探针局限**，见结论 3 |
| 6 | LongCat AI | ✅ pass 2841ms | ✅ pass 2753ms | `div[role="textbox"]`｜`div[contenteditable="true"]` | ⚠️ 未发现发送按钮类元素——需人工确认 |
| 7 | 千问 Qianwen | ✅ pass 3458ms | ✅ pass 3099ms | `div[data-slate-editor="true"]`｜`div[contenteditable="true"]` | ✅ `aria=发送消息`（**两轮都是中文**） |
| 8 | 文心一言 Yiyan | ✅ pass 3218ms | ✅ pass 2729ms | `textarea.ci-textarea`｜`textarea` | ⚠️ 未发现发送按钮类元素——需人工确认 |
| 9 | 腾讯元宝 Yuanbao | ✅ pass 31228ms | ✅ pass 3295ms | `div.ql-editor`｜`div[contenteditable="true"]` | zh ⚠️ 探测不可用（`click` 超时 30s）／en ⚠️ 未发现发送按钮类元素 |
| 10 | 智谱清言 ChatGLM | ✅ pass 31796ms | ✅ pass 3630ms | `textarea` | zh ⚠️ 探测不可用（`click` 超时 30s）／en ⚠️ 未发现发送按钮类元素 |

判定口径：`pass` = 生产 adapter 在真机 DOM 上找到输入框；`login_wall` / `bot_check` =
**未验证**（环境限制，不计失败）；`no_composer` = 疑似漂移。

**汇总**：zh-CN `pass=7 未验证=3 失败=0`；en-US `pass=7 未验证=3 失败=0`。

### 三家未验证的具体原因（**不是 adapter 的结论**）

| 平台 | 信号 | 为什么未验证 |
|------|------|--------------|
| ChatGPT | `http-status-403` | 匿名访问撞人机校验页，DOM 契约根本没机会被验证 |
| Claude.ai | `http-status-403` | 同上 |
| DeepSeek | `login_wall` | 到达站点但落在登录墙 |

这三家要出结论，**必须有已登录的浏览器 profile**——这正是 L2 那一层要解决的事。

### 测试结论

- **L1 探针本身**：双语言各 10 平台，20 次判定全部按预期落口径；
  `verify --run-id RMR-2026-10-26-01` 对账通过（20 条记录，结论 `partial`——
  **partial 的唯一原因是 L2 尚未记录**，见下）。
- **观测器改动**：`node tests/run-tests.mjs` → **125 passed**
  （其中 `l2-model.test.mjs` 31 条，新增 13 条覆盖登录判定与语言判定）。
- **回归对账**：`python3 scripts/real_machine_regression.py verify --run-id RMR-2026-10-26-01`
  明确指出「10 个平台缺 L2 记录」——**这条对账是有效的**，它在等 L2。

### 本轮未做（L2 的活）

L2 = 真人登录 + 真人发送。第 1 轮按实测结论调整为
**千问 zh-CN + Gemini en-US**（而不是原定的「千问 × 2 语言」——理由见结论 1、2），
在**同一个浏览器实例**里一次跑完（登录也在观测器内部等待，避免
「关—开」之间 cookie 落盘不可靠）。

---

## 风险

1. **「未验证」的三家仍无结论**（ChatGPT / Claude.ai / DeepSeek）——它们需要登录态，
   而登录态又需要人。第 1 轮不覆盖，属于已知缺口，不是不合格。
2. **发送按钮子探针时序敏感**——同一份代码在 zh-CN 下 `click` 超时、在 en-US 下给出结论
   （Yuanbao / ChatGLM）。**凡是「探测不可用」的行都不能当结论用**；需要给子探针
   单独的加载预算，或在结论里显式标注「不可用 ≠ 漂移」。
3. **LongCat / 文心一言的发送按钮**「未发现发送按钮类元素」——是站点形状变了，还是
   我们的探针选择器过时了，**只读探针分不出来**，必须人工在真机上确认一次。
4. **千问的 L1 结论建立在匿名首屏上**——登录后的对话页 DOM 可能有差异，
   L1 的 pass **不能**外推到登录态。
5. **本轮全部是 L1**：真实发送链路（发出去 → 等回复 → 取正文）**仍未被机器验证过**。

---

## 回滚

- 本次只新增了证据文件与一条 run 记录，回滚＝删掉这四个文件：
  ```bash
  rm collaboration/results/real-machine-runs/RMR-2026-10-26-01.json
  rm collaboration/results/real-machine-runs/evidence/L1-2026-10-26-{zh-CN,en-US}.json
  ```
- 观测器改动在 PR #5 的分支上，未合入 main；回滚＝`git revert` 对应提交
  （`feat(real-machine): L2 观测器改成「一个浏览器跑完整轮」`）。
- **未改动任何生产代码**：`src/platforms/*.js`、`src/content/*`、`src/background/*` 一行未动，
  本轮全部是**观测**与**记录**。
