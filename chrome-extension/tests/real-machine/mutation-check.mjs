/**
 * 变异检查（mutation check）
 *
 * ## 为什么要有这个
 *
 * 一套全绿的测试**什么都不能证明**——除非你能证明：
 * 「把被守护的那处代码改坏，对应的测试会变红」。
 *
 * 本仓的教训是具体的：110/114 全绿的模拟层矩阵，
 * 掩盖了 4 个真机上才暴露的生产缺陷（yiyan/yuanbao 的消息数被界面外壳撑大、
 * kimi/chatglm 的 isTyping 恒为 true）。绿不是因为对，是因为没测到。
 *
 * 所以这个脚本把「守护关系」本身变成可执行的：
 * 每条变异都对应一个**具体缺陷**，改坏它，必须有**具体那条测试**变红。
 *
 * ## 它怎么跑
 *
 * 对每个变异：
 *   1. 把 `tests/` 整棵树复制到一份**临时副本**里（不动工作区——
 *      就地改坏再就地还原的话，中途崩了就留下半个坏文件）；
 *   2. 在副本上把 `find` 替换成 `replace`（替换不到就直接失败——
 *      说明变异描述与代码脱节了，这本身就是一条要修的账）；
 *   3. 跑对应的测试文件；
 *   4. 要求**指定的那条测试**被报为失败（不是「随便哪条失败」）——
 *      否则测试可能在因为别的原因红，守护关系就没被真正验证；
 *   5. 还原副本。
 *
 * 临时副本放在 `chrome-extension/.mutation-tmp/` 下面而不是系统临时目录：
 * Node 靠**逐级向上**找 node_modules，放到 /tmp 就找不到 jsdom 了。
 *
 * 退出码：0 = 全部变异都被杀死；1 = 有变异存活（守护有洞）。
 *
 * ## WorkBuddy 沙箱里跑的坑（2026-11-10 实锤）
 *
 * 收尾的 `rmSync(.mutation-tmp)` 一次删 182 个文件，会撞上
 * WorkBuddy 的 safe-delete shim（阈值 50）⇒ 抛
 * `SAFE_DELETE_BULK_CONFIRM_REQUIRED` ⇒ **进程退出码 1，但断言本身已全绿**
 * （日志里 76 条 ✓、0 条 ✗ 才是结论，别只看退出码）。
 * 想拿干净的 0：
 *   `CODEBUDDY_SAFE_DELETE_ENABLED=0 node tests/real-machine/mutation-check.mjs`
 * （2026-11-10 21:46 实测有效：76/76 被杀死、`EXIT_CODE=0`、临时目录自动清理。）
 * 若已被拦，手工清残留：`rm -rf chrome-extension/.mutation-tmp`。
 *
 * 用法：node tests/real-machine/mutation-check.mjs
 */

import {
  readFileSync,
  writeFileSync,
  renameSync,
  existsSync,
  cpSync,
  rmSync,
  mkdirSync,
} from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const HERE = dirname(fileURLToPath(import.meta.url));
const TESTS_ROOT = resolve(HERE, "..");
const EXT_ROOT = resolve(TESTS_ROOT, "..");
const TMP_ROOT = join(EXT_ROOT, ".mutation-tmp");

/**
 * 变异清单。
 *
 * 每条写清：改坏哪一处、对应哪个真实缺陷、哪条测试必须因此变红。
 * `expectTest` 必须是**具体测试名**——只要求「有测试失败」是不够的。
 */
const MUTATIONS = [
  // ── L2 判定逻辑 ──────────────────────────────────────────────
  {
    name: "把「计数增长」从 > 改成 >=（判定报告位）",
    why: "生产口径是严格大于；报告位改成 >= 会把「一条都没多」谎报成 countGrew",
    target: "real-machine/l2-model.mjs",
    find: "usable.some((s) => s.messageCount > initial)",
    replace: "usable.some((s) => s.messageCount >= initial)",
    testFile: "real-machine/l2-model.test.mjs",
    expectTest: "生成中解除但计数没涨",
  },
  {
    name: "把「计数增长」从 > 改成 >=（重放放行位）",
    why: "重放放行位改成 >= 会把「一条都没多」的稳定正文时间线误判为已回复——这就是「误判为已回复」的产生点",
    target: "real-machine/l2-model.mjs",
    find: "countGrew: s.messageCount > initial,",
    replace: "countGrew: s.messageCount >= initial,",
    testFile: "real-machine/l2-model.test.mjs",
    expectTest: "生成中解除但计数没涨",
  },
  {
    name: "把「不在生成中」这个条件去掉",
    why: "去掉后稳定窗一到就返回，不管还在不在生成中——思考停顿期就会提前取走半截正文，这正是 isTyping 选错时的真实故障模式",
    target: "real-machine/l2-model.mjs",
    find: "if (state.ready && s.isTyping === false) {",
    replace: "if (state.ready) {",
    testFile: "real-machine/l2-model.test.mjs",
    expectTest: "计数涨了但 isTyping 恒为 true",
  },
  {
    name: "基准不再取生产启动那一刻的计数",
    why: "退回用第一个采样做基准，中间落进一条消息就会被误判为「没增长」",
    target: "real-machine/l2-model.mjs",
    find: "typeof baselineCount === \"number\"",
    replace: "false",
    testFile: "real-machine/l2-model.test.mjs",
    expectTest: "基准取生产启动那一刻的计数",
  },
  {
    name: "生产取到的正文非空判定恒为真",
    why: "恒为真会让「等待成功但正文是空」这种缺陷被判为通过",
    target: "real-machine/l2-model.mjs",
    find: "productionContentNonEmpty: Boolean(prodResult && (prodResult.content || \"\").trim().length > 0),",
    replace: "productionContentNonEmpty: true,",
    testFile: "real-machine/l2-model.test.mjs",
    expectTest: "productionContentNonEmpty 揪出抽取断链",
  },
  {
    name: "证据文件不再脱敏",
    why: "真实会话正文会进 git 仓库，不脱敏等于把个人信息公开",
    target: "real-machine/l2-model.mjs",
    find: "lastContent: typeof s.lastContent === \"string\" ? sanitizeText(s.lastContent) : \"\",",
    replace: "lastContent: typeof s.lastContent === \"string\" ? s.lastContent : \"\",",
    testFile: "real-machine/l2-model.test.mjs",
    expectTest: "证据文件里正文被脱敏",
  },
  {
    name: "证据文件谎称脚本发过消息",
    why: "sendsMessages 是给审阅者看的机器可读声明，写错等于伪造证据",
    target: "real-machine/l2-model.mjs",
    find: "sendsMessages: false,",
    replace: "sendsMessages: true,",
    testFile: "real-machine/l2-model.test.mjs",
    expectTest: "证据文件里正文被脱敏",
  },
  {
    name: "一致位恒为真",
    why: "一致性是发现「生产结果与时间线对不上」的唯一信号",
    target: "real-machine/l2-model.mjs",
    find: "consistent: settled === (resolveAtIndex !== null),",
    replace: "consistent: true,",
    testFile: "real-machine/l2-model.test.mjs",
    expectTest: "生产结果与时间线重放不一致时",
  },
  {
    name: "--i-will-send 闸门失效",
    why: "没有这个闸门，误跑一次就会在真站上发出一条真实消息",
    target: "real-machine/l2-model.mjs",
    find: "} else if (raw === \"--i-will-send\") {\n      args.iWillSend = true;",
    replace: "} else if (raw === \"--i-will-send\") {\n      args.iWillSend = false;",
    testFile: "real-machine/l2-model.test.mjs",
    expectTest: "--i-will-send 会打开发送闸门",
  },

  // ── 消息计数模型（两条不变量）────────────────────────────────
  {
    name: "「命中元素必须无文本」这条硬伤判定阈值收紧到永不触发",
    why: "去掉后 Yiyan 的 _chat-container_ 这类界面外壳会被当成消息，计数被撑起来",
    target: "real-machine/message-model.mjs",
    find: ".filter((x) => (x.textLength ?? 0) > 0)",
    replace: ".filter((x) => (x.textLength ?? 0) > 9999)",
    testFile: "real-machine/message-model.test.mjs",
    expectTest: "命中界面外壳（Yiyan 的 _chat-container_）",
  },
  {
    name: "去掉「空闲即不忙」这条硬伤判定",
    why: "去掉后 isTyping 恒为 true 的平台会被判为合格，而每次发送都必然超时",
    target: "real-machine/message-model.mjs",
    find: "if (typing === true) {",
    replace: "if (false) {",
    testFile: "real-machine/message-model.test.mjs",
    expectTest: "空闲页上 isTyping 为 true",
  },

  // ── 脱敏器 ──────────────────────────────────────────────────
  {
    name: "class 属性重新开始做长随机串脱敏",
    why: "CSS Module 的哈希类名是结构不是令牌，误脱敏会毁掉选择器的命中依据",
    target: "real-machine/sanitize.mjs",
    find: "if (STRUCTURAL_ATTRS.has(String(name).toLowerCase())) {",
    replace: "if (false) {",
    testFile: "real-machine/sanitize.test.mjs",
    expectTest: "class 属性不做长随机串脱敏",
  },
  {
    name: "邮箱规则失效",
    why: "真实 DOM 快照要进 git 仓库，邮箱漏出去就是个人信息泄露",
    target: "real-machine/sanitize.mjs",
    find: "/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}/g",
    replace: "/(?!x)x/g",
    testFile: "real-machine/sanitize.test.mjs",
    expectTest: "邮箱被替换",
  },

  // ── 千问 adapter 的选择器（2026-10-25 真机实测 B-3）────────────
  //
  // 下面 6 条全部打在**生产源码**上（target 以 "src/" 开头）：
  // 原选择器在千问自己的 56 个资源 / 15.45 MB 里一次都没出现过（普查见
  // tests/real-machine/evidence/qianwen-asset-census.json），
  // 而千问的会话 DOM 采不到（需要已登录 profile），所以只能靠
  // 「从站点产物推导的契约 fixture」来守——那套 fixture 一旦没人守，
  // 生产选择器就会重新漂回那些命中 0 个的类名，而且**不会有人发现**。
  {
    name: "把千问的消息选择器退回宽松的 [class*=\"message\"]",
    why: "宽松选择器会命中 message-list-container 这类界面外壳，消息数被撑大（yiyan/yuanbao 的同款病）",
    target: "src/platforms/qianwen-adapter.js",
    find: "    'div.answer-text.md-text-card',",
    replace: "    '[class*=\"message\"]',",
    testFile: "real-machine/qianwen-contract.test.mjs",
    expectTest: "消息数只算答案卡",
  },
  {
    name: "把千问的正文选择器退回只取第一段",
    why: "只取 .qk-md-text 只能拿到 markdown 的第一段，多段落答案被截断",
    target: "src/platforms/qianwen-adapter.js",
    find: "    '.qk-markdown',",
    replace: "    '.qk-md-text',",
    testFile: "real-machine/qianwen-contract.test.mjs",
    expectTest: "答案正文取整个 markdown 容器",
  },
  {
    name: "把千问的发送按钮选择器退回依赖本地化文案",
    why: "aria-label 随界面语言变（站点词典 sendMessage = 发送消息 / 傳送訊息），英文界面下必然落空",
    target: "src/platforms/qianwen-adapter.js",
    find: "    'button[data-session-switch-target=\"send-query\"]',\n",
    replace: "",
    testFile: "real-machine/qianwen-contract.test.mjs",
    expectTest: "发送按钮靠稳定属性命中",
  },
  {
    name: "把千问的「停止回答」选择器改坏",
    why: "生成中的信号是输入区那个「停止回答」按钮；认不出来就会在回复没写完时提前返回",
    target: "src/platforms/qianwen-adapter.js",
    find: "    'button[aria-label*=\"停止回答\"]',",
    replace: "    'button[aria-label*=\"发送消息\"]',",
    testFile: "real-machine/qianwen-contract.test.mjs",
    expectTest: "识别停止回答按钮",
  },
  {
    name: "把千问的「接收中卡片」选择器改坏",
    why: "等待首个 token 期间是接收中点点点卡片，它必须能被认成生成中",
    target: "src/platforms/qianwen-adapter.js",
    find: "    'div.answer-receiving-card',",
    replace: "    'div.answer-receiving-card-typo',",
    testFile: "real-machine/qianwen-contract.test.mjs",
    expectTest: "只有接收中卡片",
  },
  {
    name: "把千问正文的「先看元素自身」这一步去掉",
    why: "markdown 容器与答案卡是同一个元素时，只查后代会漏掉它，退到 .qk-md-text 就只拿到第一段",
    target: "src/platforms/qianwen-adapter.js",
    find: "      const self = element.matches?.(sel) ? element : null;",
    replace: "      const self = null;",
    testFile: "real-machine/qianwen-contract.test.mjs",
    expectTest: "markdown 容器与答案卡是同一个元素时也能取到完整正文",
  },

  // ── 后台 ↔ 内容脚本 的消息协议 ──────────────────────────────
  //
  // 2026-10-25 查 Pack 执行链路时发现的那条断线：后台发 SEND_TO_AI，
  // 内容脚本没有分支处理 ⇒ 消息发出去没人接 ⇒ AI 步骤拿到空值却被
  // 当成成功 ⇒ Pack「执行成功」但产物是空的。
  //
  // 这条变异把分支删掉，用同一条测试证明「真删了就会红」——
  // 否则这条修复只是一次「看着对」的接线，没有证据。
  //
  // 🔧 2026-11-11：锚点从「整段 handler 文本」改成「只改 case 标签」。
  // 原锚点是一段 8 行的 find 字面量，只要 handler 内部改一行（本轮就改了超时取值），
  // 锚点就悄悄失配——变异器会把它记成「存活」，看起来像守护有洞，实际是锚点漂移。
  // 改 case 标签只需一行，语义同样是「这条消息没人认了」，但不会随实现细节漂。
  {
    name: "把内容脚本的 SEND_TO_AI 分支删掉",
    why: "后台的 AI 步骤靠它才能拿到 AI 的回复；删了 Pack 执行链路就断",
    target: "src/content/content-script.js",
    find: '      case "SEND_TO_AI":\n',
    replace: "",
    testFile: "extension-wiring.test.mjs",
    expectTest: "Pack 的 AI 步骤发的那条消息",
  },
  {
    name: "把内容脚本的 SEND_TO_AI 改成不注入文本",
    why: "不注入就等于什么都没发出去，AI 会答非所问",
    target: "src/content/content-script.js",
    find: "  await handleInjectText(prompt);\n",
    replace: "",
    testFile: "extension-wiring.test.mjs",
    expectTest: "提示词进了输入框",
  },
  {
    name: "执行器不再从 storage 同步 Pack",
    why: "Pack 的事实源是 storage 不同步就是 'Pack not found'——用户点执行只会看到这一句",
    target: "src/background/service-worker.js",
    find: "  return packExecutor.replacePacks(packs);",
    replace: "  return packExecutor.replacePacks([]);",
    testFile: "extension-wiring.test.mjs",
    expectTest: "storage 里的 Pack 要能被执行器找到并执行",
  },
  {
    name: "popup 又用回不存在的 pack.id",
    why: "Pack 的 id 在 metadata.pack_id 里；用 pack.id 会渲染出 data-id=\"undefined\"",
    target: "public/popup.js",
    find:
      "        const id = pack.metadata?.pack_id || '';",
    replace: "        const id = pack.id || '';",
    testFile: "extension-wiring.test.mjs",
    expectTest: "popup 渲染出来的 data-id",
  },
  {
    name: "导入 Pack 的 ID 判据退回双轨",
    why: "IMPORT_PACKS 一旦又放行顶层 pack_id，就会出现「导入报成功、UI 列得出、点运行必 Pack not found」——中间只有 console.warn 一条线索；而且报错文案写着「缺少 metadata.pack_id」，判据却认 pack.pack_id，文案与行为自相矛盾",
    target: "src/background/service-worker.js",
    find: "            const packId = pack.metadata?.pack_id;",
    replace: "            const packId = pack.metadata?.pack_id || pack.pack_id;",
    testFile: "pack-import-gate.test.mjs",
    expectTest: "只带顶层 pack_id 的 Pack 必须被拒，且报错指出缺 metadata.pack_id",
  },
  {
    name: "public 下的脚本里写坏一个语法",
    why: "vite 对 public/ 是原样复制，语法错不会被构建发现——会一路发到用户手里",
    target: "public/popup.js",
    find: "const packList = document.getElementById('packList');",
    replace: "const packList = document.getElementById('packList');)",
    testFile: "extension-wiring.test.mjs",
    expectTest: "public/ 下的脚本必须语法正确",
  },
  {
    name: "AI 步骤退回广播（不再定向到标签页）",
    why:
      "广播会让用户开着几个 AI 页面就收到几次提示词——" +
      "第一次用的人看到的是「这扩展在乱发消息」",
    target: "src/background/pack-executor.js",
    find: "    if (targetTabId !== null && targetTabId !== undefined) {",
    replace: "    if (false) {",
    testFile: "extension-wiring.test.mjs",
    expectTest: "AI 步骤要发到指定标签页",
  },
  {
    name: "后台不再把目标标签页传给执行器",
    why: "目标标签页一路传到执行器才有意义，中间断一截就退回广播",
    target: "src/background/service-worker.js",
    find: "              { tabId: message.tabId ?? null },",
    replace: "              {},",
    testFile: "extension-wiring.test.mjs",
    expectTest: "后台要把目标标签页一路传到 AI 步骤",
  },
  {
    name: "popup 不再把当前标签页告诉后台",
    why: "popup 拿不到 tabId，后台就只能广播",
    target: "public/popup.js",
    find: "      type: 'EXECUTE_PACK',\n      packId,\n      tabId,\n      input: input || {}",
    replace: "      type: 'EXECUTE_PACK',\n      packId,\n      tabId: null,\n      input: input || {}",
    testFile: "extension-wiring.test.mjs",
    expectTest: "popup 要把用户当前所在的标签页告诉后台",
  },
  {
    name: "popup 不再打开 Pack 编辑器",
    why: "popup 是外部用户看到的第一屏；没有导入入口就卡在第一步",
    target: "public/popup.js",
    find: "      url: chrome.runtime.getURL('pack-editor.html')",
    replace: "      url: 'about:blank'",
    testFile: "extension-wiring.test.mjs",
    expectTest: "popup 必须有「导入 Pack」的入口",
  },
  {
    name: "getURL 退回嵌套布局",
    why:
      "产物是扁平布局，getURL('public/...') 在装好的扩展里 404；" +
      "「导入 Pack」「风格编辑器」直接断掉",
    target: "public/popup.js",
    find: "      url: chrome.runtime.getURL('pack-editor.html')",
    replace: "      url: chrome.runtime.getURL('public/pack-editor.html')",
    testFile: "extension-wiring.test.mjs",
    expectTest: "代码里 getURL 指到的页面，在构建产物里必须真的存在",
  },
  {
    name: "把交付给外部用户的冒烟 Pack 的提示词改掉",
    why:
      "外部用户拿到的就是这份 Pack；提示词一旦对不上，AI 复述的" +
      "就不是指南里写的那句，「冒烟自检通过」的判据整个失效",
    target: "packs/examples/external-user-smoke.json",
    find: "请只回复这一句话，不要添加任何其他内容：你好，Prompt Pack 冒烟自检通过。",
    replace: "随便说点什么",
    testFile: "extension-wiring.test.mjs",
    expectTest: "交付给外部用户的那个冒烟 Pack",
  },
  {
    name: "D5 解包退回（定向标签页路径返回整个信封）",
    why:
      "D5 之前 _executeAIStep 把整条回话信封原样返回，" +
      "于是 final_content 里是 6 个 [object Object]——用户看到的成品正文是一串占位符。" +
      "修法是只取 response.result.content；退回去就等于把这个缺陷放回来",
    target: "src/background/pack-executor.js",
    find:
      "      assertAIStepSucceeded(response, targetTabId);\n" +
      '      const content = response?.result?.content ?? "";\n' +
      "      assertUsableAIContent(content, step, targetTabId);\n" +
      "      return content;",
    replace:
      "      assertAIStepSucceeded(response, targetTabId);\n" +
      "      return response;",
    testFile: "pack-step-types.test.mjs",
    expectTest: "_executeAIStep 解包回复内容，output 全为文本且无 [object Object]",
  },
  {
    name: "D5 解包退回（广播路径返回整个信封）",
    why:
      "同上，但走的是「没有目标标签页」那条广播分支——" +
      "两条 return 都得守，只守一条等于 D5 只修了一半",
    target: "src/background/pack-executor.js",
    find:
      "    assertAIStepSucceeded(response, null);\n" +
      '    const content = response?.result?.content ?? "";\n' +
      "    assertUsableAIContent(content, step, null);\n" +
      "    return content;",
    replace:
      "    assertAIStepSucceeded(response, null);\n" +
      "    return response;",
    testFile: "extension-wiring.test.mjs",
    expectTest: "没有目标标签页时才广播，并且要标明是广播",
  },

  // ── 内容稳定性等待 + 碎片判失败（2026-11-04 千问真机实锤）──────
  //
  // 真机首跑 8 步 Pack 全部「成功」而产物是 7 段 '收到，' 碎片 + 1 个空串：
  // 旧判据「消息数增加 且 不在生成中」在流式开口瞬间就放行。
  // 下面三条变异分别把三道新闸门拆掉，证明测试真的守着它们。
  {
    name: "碎片/空内容判定失效（恒可用）",
    why: "'收到，' 这种流式开头碎片冒充完成的回复；闸门失效就等于把缺陷放回来",
    target: "src/utils/wait-policy.js",
    find: "  return text.length >= minLen;",
    replace: "  return true;",
    testFile: "external-user-path.test.mjs",
    expectTest: "AI 步骤取回流式开头碎片时，整个 Pack 必须失败",
  },
  {
    name: "空内容也判完成",
    why: "空串是「还没开始流」（千问实跑里 step_6 的空产物就是这么来的），判完成就会把空串当回复取走",
    target: "src/utils/wait-policy.js",
    find: "text.length > 0 && nextLastChangeAt != null",
    replace: "true && nextLastChangeAt != null",
    testFile: "wait-policy.test.mjs",
    expectTest: "空内容永不判完成（防把流式开头当回复）",
  },
  {
    name: "稳定窗口失效（内容一出现就算完成）",
    why: "退回「内容非空即完成」就又变成太早成功——流式开头恰好是非空的",
    target: "src/utils/wait-policy.js",
    find: "now - nextLastChangeAt >= stableMs;",
    replace: "true;",
    testFile: "wait-policy.test.mjs",
    expectTest: "内容还在变化时不判完成",
  },

  // ── 第二轮：生成中状态行 + 抽取契约 + 阈值/稳定窗（2026-11-04）────
  //
  // 真机第二轮（清缓存干净复跑）实锤的三重绕过：ack 混入状态条文本
  // 25–41 字压线过 20 字闸、稳定窗在「努力工作中」思考停顿里放行、
  // 抽取 fallback 把状态条当正文。下面六条变异把六道新闸门逐个拆掉。
  {
    name: "千问生成中状态行选择器被删（努力工作中不被认出）",
    why:
      "「✨ 努力工作中 用时N秒」是 claw-desktop-main.js 状态行按钮的 " +
      "data-status=working——删掉它就是在思考停顿期盲放行，抓走的全是 ack",
    target: "src/platforms/qianwen-adapter.js",
    find: "    'button[data-status=\"working\"]',\n",
    replace: "",
    testFile: "real-machine/qianwen-contract.test.mjs",
    expectTest: "生成中状态行（data-status=working）也判定 isTyping()",
  },
  {
    name: "adapter-utils 抽取契约收紧失效（恢复全卡回退）",
    why: "回退整卡 textContent 就会把「正在思考中/努力工作中」状态条混进正文（真机第二轮 step_2/3 污染实锤）",
    target: "src/platforms/adapter-utils.js",
    find: "  if (contentSelectors.length > 0) return '';",
    replace: "  if (contentSelectors.length > 0) return messageElement.textContent?.trim() || '';",
    testFile: "real-machine/qianwen-contract.test.mjs",
    expectTest: "extractMessageContent 同样不许回退整卡文本",
  },
  {
    name: "adapter-utils 自身匹配被删（容器=正文同体丢段落）",
    why: "只查后代会漏掉「容器本身就是 markdown」的形态，退回全卡文本又把状态条带进来",
    target: "src/platforms/adapter-utils.js",
    find: "    const self = messageElement.matches?.(selector) ? messageElement : null;",
    replace: "    const self = null;",
    testFile: "real-machine/qianwen-contract.test.mjs",
    expectTest: "extractMessageContent 先看元素自身再查后代",
  },
  {
    name: "千问 _extractContent 契约收紧失效（恢复全卡回退）",
    why: "与 adapter-utils 同步的另一半——只堵一处等于没堵",
    target: "src/platforms/qianwen-adapter.js",
    find:
      "      if (el) return el.textContent.trim();\n" +
      "    }\n" +
      '    return "";',
    replace:
      "      if (el) return el.textContent.trim();\n" +
      "    }\n" +
      "    return element.textContent?.trim() || \"\";",
    testFile: "real-machine/qianwen-contract.test.mjs",
    expectTest: "选择器未命中时不许回退整卡文本（状态条不许混进正文）",
  },
  {
    name: "碎片阈值回退（50→20）",
    why: "20 分不开 ack 与正文——真机第二轮 ack 带主题词 20–26 字、混状态条 25–41 字全部压线过闸",
    target: "src/utils/wait-policy.js",
    find: "export const MIN_AI_CONTENT_LENGTH_DEFAULT = 50;",
    replace: "export const MIN_AI_CONTENT_LENGTH_DEFAULT = 20;",
    testFile: "external-user-path.test.mjs",
    expectTest: "污染 ack 混入状态条文本也不许冒充正文",
  },
  {
    name: "稳定窗回退（8s→4s）",
    why: "4 秒窗在「努力工作中」思考停顿里被误判成生成结束（真机第二轮复跑 6/7 产出是 ack 的直接原因）",
    target: "src/utils/wait-policy.js",
    find: "export const STABLE_MS_DEFAULT = 8000;",
    replace: "export const STABLE_MS_DEFAULT = 4000;",
    testFile: "wait-policy.test.mjs",
    expectTest: "默认稳定窗是 8 秒：5 秒定格不算完成，8 秒才算（防思考停顿误判）",
  },
  {
    name: "popup 产出渲染被删（N13 复发：只报状态丢产出）",
    why: "executePack 只写「执行成功」就丢掉 response.result.output——外部用户点了运行拿不到任何产物（台账 N13 原始缺陷）",
    target: "public/popup.js",
    find: "const count = renderOutputs(response.result?.output);",
    replace: "const count = 0;",
    testFile: "extension-wiring.test.mjs",
    expectTest: "popup 执行成功必须展示产出",
  },
  {
    name: "产出渲染回退 innerHTML（模型文本注入面）",
    why: "产出是不可信的模型文本，走 innerHTML 就是给 popup 开注入面（台账 N2 同类）",
    target: "public/popup.js",
    find: "body.textContent = text;",
    replace: "body.innerHTML = text;",
    testFile: "extension-wiring.test.mjs",
    expectTest: "产出文本必须走 textContent",
  },
  {
    name: "复制按钮丢字段（复制不到全文）",
    why: "复制按钮必须把该字段全文（不是片段/空串）写进剪贴板",
    target: "public/popup.js",
    find: "copyOutputField(btn.dataset.copyField);",
    replace: "copyOutputField('');",
    testFile: "extension-wiring.test.mjs",
    expectTest: "产出复制按钮把该字段全文放进剪贴板",
  },
  {
    name: "导出 JSON 丢产出（导出空对象）",
    why: "导出必须是全量产出 JSON——导出空对象等于换了个姿势丢产物",
    target: "public/popup.js",
    find: "const json = JSON.stringify(lastOutputs, null, 2);",
    replace: "const json = JSON.stringify({}, null, 2);",
    testFile: "extension-wiring.test.mjs",
    expectTest: "导出 JSON 按钮产出全量产出 JSON",
  },
  {
    name: "generic 等待回退旧判据（太早成功复辟）",
    why: "「计数增长且不在生成中」在流式第一帧就返回——台账 N14 太早成功的原始判据",
    target: "src/platforms/adapter-utils.js",
    find: "if (state.ready && !isTyping()) {",
    replace: "if (messages.length > initialCount && !isTyping()) {",
    testFile: "adapter-wait.test.mjs",
    expectTest: "内容没稳住不许返回",
  },
  {
    name: "基类委托被改空（钩子全文丢失）",
    why: "waitForResponse 必须把 _extractContent 钩子的全文带回来——带不回全文等于取回断链",
    target: "src/platforms/adapter.js",
    find: "extractContent: (el) => this.extractMessage(el),",
    replace: "extractContent: () => \"\",",
    testFile: "adapter-wait.test.mjs",
    expectTest: "基类 waitForResponse 必须走 _extractContent 钩子取全文",
  },
  {
    name: "抽取钩子优先级丢失（兜底吞掉子类抽取）",
    why: "子类 _extractContent 是抽取第一优先——被兜底吞掉就是各平台抽取细节全丢",
    target: "src/platforms/adapter.js",
    find: "if (typeof this._extractContent === 'function') return this._extractContent(element);",
    replace: "if (false) return this._extractContent(element);",
    testFile: "adapter-wait.test.mjs",
    expectTest: "基类 waitForResponse 必须走 _extractContent 钩子取全文",
  },
  {
    name: "l2-model 重放回退旧口径（重放与生产分叉）",
    why: "观测器重放必须走 sampleWaitState 同一判据——回退旧口径就又造出第二把尺子",
    target: "real-machine/l2-model.mjs",
    find: "if (state.ready && s.isTyping === false) {",
    replace: "if (s.messageCount > initial && s.isTyping === false) {",
    testFile: "real-machine/l2-model.test.mjs",
    expectTest: "内容持续在变的流式时间线不许判成功",
  },

  // ── typingIndicator 普查证据（2026-11-04 五平台零发送静态普查）──
  {
    name: "Kimi 生成中状态行选择器被删",
    why: "segment-generate-tip 是服务端状态机 tips 文案流的渲染载体——删掉它，思考停顿期 isTyping 盲放行（N14 同类缺陷）",
    target: "src/platforms/kimi-adapter.js",
    find: "    \".segment .segment-generate-tip\",\n",
    replace: "",
    testFile: "typing-indicator-contract.test.mjs",
    expectTest: "Kimi：segment-generate-tip 生成中状态行",
  },
  {
    name: "Kimi 通用加载组件被误收进 typingIndicator",
    why: "core-spiral-loading 在历史列表/文件卡多处复用——收进来空闲页恒 true ⇒ 每次等待必超时",
    target: "src/platforms/kimi-adapter.js",
    find: "    \".send-button-container.stop\",\n",
    replace: "    \".send-button-container.stop\",\n    \".core-spiral-loading\",\n",
    testFile: "typing-indicator-contract.test.mjs",
    expectTest: "core-spiral-loading（历史/文件卡复用，无 role=status）不许算生成中",
  },
  {
    name: "ChatGLM 停止按钮选择器丢掉 button 标签限定",
    why: "div.sensitive[ga-data=\"stop\"] 是内容安全敏感态同名属性——不加 button 限定就误命中，敏感页恒 true",
    target: "src/platforms/chatglm-adapter.js",
    find: "    'button[ga-data=\"stop\"]',\n",
    replace: "    '[ga-data=\"stop\"]',\n",
    testFile: "typing-indicator-contract.test.mjs",
    expectTest: "div.sensitive[ga-data=stop]（内容安全敏感态）不许算生成中",
  },
  {
    name: "ChatGLM 停止回答按钮选择器被删",
    why: "StopGenerator 的 button ga-data=stop 是「生成中⇔存在」的最强信号——删掉它，太早成功闸破防",
    target: "src/platforms/chatglm-adapter.js",
    find: "    'button[ga-data=\"stop\"]',\n",
    replace: "",
    testFile: "typing-indicator-contract.test.mjs",
    expectTest: "ChatGLM：button ga-data=stop 停止回答按钮",
  },
  {
    name: "文心 thinking-loading 自定义元素选择器被删",
    why: "「正在思考」加载行挂自定义元素 thinking-loading 上——删掉标签选择器，思考期盲放行",
    target: "src/platforms/yiyan-adapter.js",
    find: "    \"thinking-loading\",\n",
    replace: "",
    testFile: "typing-indicator-contract.test.mjs",
    expectTest: "文心：thinking-loading 自定义元素",
  },
  {
    name: "文心 停止回答按钮选择器被删",
    why: "answer-generate-state-button[data-module=stop] 是生成中⇔存在的判定——删掉就退回猜测类名时代",
    target: "src/platforms/yiyan-adapter.js",
    find: "    '.answer-generate-state-button[data-module=\"stop\"]',\n",
    replace: "",
    testFile: "typing-indicator-contract.test.mjs",
    expectTest: "文心：停止回答按钮（answer-generate-state-button",
  },
  {
    name: "LongCat 停止生成按钮选择器被删",
    why: "stop-generate 仅 LOADING||OUTPUT 挂载——覆盖思考全期，删掉后流式中途盲放行",
    target: "src/platforms/longcat-adapter.js",
    find: "    '[class*=\"stop-generate\"]',\n",
    replace: "",
    testFile: "typing-indicator-contract.test.mjs",
    expectTest: "LongCat：stop-generate 停止生成按钮",
  },
  {
    name: "LongCat reason-title 排除决策被撤销",
    why: "reason-title 思考完成后元素保留（文案变『已深度思考』）——收进来 isTyping 恒 true ⇒ 每次必超时",
    target: "src/platforms/longcat-adapter.js",
    find: "    '[class*=\"loading-dot-box\"]',\n",
    replace: "    '[class*=\"reason-title\"]',\n    '[class*=\"loading-dot-box\"]',\n",
    testFile: "typing-indicator-contract.test.mjs",
    expectTest: "思考完成后的 reason-title（文案变『已深度思考』）不许算生成中",
  },
  {
    name: "元宝 data-conv-outputting 状态属性选择器被删",
    why: "data-conv-speaker=ai + data-conv-outputting=true 是无哈希状态属性（最强信号）——删掉就退回宽泛类名",
    target: "src/platforms/yuanbao-adapter.js",
    find: "    '[data-conv-speaker=\"ai\"][data-conv-outputting=\"true\"]',\n",
    replace: "",
    testFile: "typing-indicator-contract.test.mjs",
    expectTest: "元宝：data-conv-outputting 状态属性",
  },
  // ── N3/N4：pack 执行器输入护栏与变量序列化（2026-11-05）──────
  {
    name: "N3：必填空串/纯空白检查被删",
    why: "空串被当齐备 ⇒ popup 留空提交照样放行，残句提示词（「主题：。」）出城——N3 缺陷的产生点",
    target: "src/background/pack-executor.js",
    find: '      if (typeof value === "string" && value.trim() === "") return true;\n',
    replace: "",
    testFile: "pack-step-types.test.mjs",
    expectTest: "_executeStep 拒绝 required_fields 缺失",
  },
  {
    name: "N4：模板变量值序列化被绕过",
    why: "对象值直接进 replace ⇒ 隐式 ToString ⇒ [object Object] 进提示词——N4 缺陷的产生点",
    target: "src/background/pack-executor.js",
    find: "          this._stringifyVarValue(key, value),\n",
    replace: "          value,\n",
    testFile: "pack-step-types.test.mjs",
    expectTest: "_buildPrompt 对对象值 JSON 序列化",
  },
  // ── N2/N8：popup 不可信数据渲染与广播标记（2026-11-05）──────────
  {
    name: "N2：输入字段名改回 innerHTML 拼接",
    why: "字段名是 Pack 作者控制的——innerHTML 会把 `<img>`/破属性当标记解析，伪造输入框骗凭据（N2 缺陷产生点）",
    target: "public/popup.js",
    find: "      label.appendChild(document.createTextNode(f));\n",
    replace: "      label.innerHTML = f;\n",
    testFile: "extension-wiring.test.mjs",
    expectTest: "N2：输入字段名含 HTML 时不得被解析",
  },
  {
    name: "N2：pack 列表 name 改回 innerHTML 拼接",
    why: "pack_name/description 同为 Pack 作者控制（台账原漏记的第二注入面）——innerHTML 会解析伪造 UI",
    target: "public/popup.js",
    find: "        nameEl.textContent = name;\n",
    replace: "        nameEl.innerHTML = name;\n",
    testFile: "extension-wiring.test.mjs",
    expectTest: "N2：pack 列表",
  },
  {
    name: "N8：广播标记谎报为 precise",
    why: "标记与真实投递方式（runtime.sendMessage 广播）脱钩 ⇒ popup 不提示，用户以为只发了一次——N8 空保证的产生点",
    target: "src/background/pack-executor.js",
    find: '            ? "precise"\n            : "broadcast",\n',
    replace: '            ? "precise"\n            : "precise",\n',
    testFile: "extension-wiring.test.mjs",
    expectTest: "没有目标标签页时才广播",
  },
  {
    name: "N8：popup 广播提示被摘除",
    why: "标记有了消费者才算真保证——摘掉 tail 提示，「要标明是广播」又变回空保证",
    target: "public/popup.js",
    find: "      const tail = broadcasted ? '（未指定标签页：提示词已广播到所有打开的 AI 页面）' : '';\n",
    replace: "      const tail = '';\n",
    testFile: "extension-wiring.test.mjs",
    expectTest: "N8：广播投递时 popup 要提示",
  },
  // ── N10：首装播种（2026-11-09）────────────────────────────────
  {
    name: "N10：首装播种调用被摘除",
    why: "摘掉 seedDefaultPacksIfEmpty() 调用，新装用户又回到零 Pack 空列表（台账 N10 原始缺陷）",
    target: "src/background/service-worker.js",
    find: "        await seedDefaultPacksIfEmpty();\n",
    replace: "",
    testFile: "extension-wiring.test.mjs",
    expectTest: "首次安装且 storage 为空时播种默认 Pack",
  },
  {
    name: "N10：空仓判定被拆掉（已有 Pack 也被覆盖）",
    why: "空仓判定失效后播种会覆盖用户已有 Pack——备份还原/侧载场景静默丢数据",
    target: "src/background/service-worker.js",
    find: "  if (packs.length > 0) return [];",
    replace: "  if (false) return [];",
    testFile: "extension-wiring.test.mjs",
    expectTest: "已有 Pack 时不许被默认 Pack 覆盖",
  },
  {
    name: "N10：update 也播种（用户删光被静默塞回）",
    why: "reason 闸门失效后每次更新都播种——用户有意删光的默认 Pack 被静默塞回来",
    target: "src/background/service-worker.js",
    find: '      if (details.reason === "install") {',
    replace: "      if (true) {",
    testFile: "extension-wiring.test.mjs",
    expectTest: "update 不播种",
  },
  // ── N20：Studio 状态区注入面（2026-11-09）─────────────────────
  {
    name: "N20：回执字段渲染回退 innerHTML（标记注入复辟）",
    why: "content_type/mode 是后端回执字段——回 innerHTML 就是给 popup 开标记注入面（N2 同机械类）",
    target: "public/popup.js",
    find: "    item.appendChild(document.createTextNode(`${icon} ${a.content_type}${mode}`));",
    replace: "    item.innerHTML = `${icon} ${a.content_type}${mode}`;",
    testFile: "extension-wiring.test.mjs",
    expectTest: "Studio 回执字段含 HTML",
  },
  {
    name: "N20：download_url 协议白名单失效（javascript: 进 href）",
    why: "白名单失效后 javascript: 伪协议进 href——台账 N20 里最实的一条注入面",
    target: "public/popup.js",
    find: "/^https?:\\/\\//i.test(a.download_url)",
    replace: "true",
    testFile: "extension-wiring.test.mjs",
    expectTest: "非 http(s) 时不许进 href",
  },
  {
    name: "N20：状态行渲染回退 innerHTML（错误串注入复辟）",
    why: "response.error / error.message 是消息层可控串——回 innerHTML 就是错误面注入复辟",
    target: "public/popup.js",
    find: "  item.textContent = text;",
    replace: "  item.innerHTML = text;",
    testFile: "extension-wiring.test.mjs",
    expectTest: "错误串（response.error / error.message）含 HTML",
  },
  // ── N11：孤儿 pack_id 残留可见化（2026-11-09）──────────────────
  {
    name: "N11：GET_ALL_PACKS 打标被摘（孤儿包伪装正常）",
    why: "不打 unrecognized:true，旧格式僵尸包就伪装成正常 Pack——台账 N11「既不可见又不可清理」的产生点",
    target: "src/background/service-worker.js",
    find: "            p.metadata?.pack_id ? p : { ...p, unrecognized: true },",
    replace: "            p,",
    testFile: "extension-wiring.test.mjs",
    expectTest: "GET_ALL_PACKS 给孤儿包打 unrecognized:true",
  },
  {
    name: "N11：popup 孤儿判定被拆（警告永不出现）",
    why: "判定恒 false 后僵尸行不再出警告，回到不可见僵尸状态",
    target: "public/popup.js",
    find: "        const unrecognized = !id;",
    replace: "        const unrecognized = false;",
    testFile: "extension-wiring.test.mjs",
    expectTest: "popup 对孤儿包出可见警告",
  },
  {
    name: "N11：popup 警告文案被摘（可见警告变哑巴）",
    why: "警告元素还在但文案为空——「可见警告」变回空保证",
    target: "public/popup.js",
    find: "          warnEl.textContent = '⚠️ 无法识别（旧格式残留，缺 metadata.pack_id）：不可执行、不可删除，数据已保留';",
    replace: "          warnEl.textContent = '';",
    testFile: "extension-wiring.test.mjs",
    expectTest: "popup 对孤儿包出可见警告",
  },

  // ── 2026-11-10 多平台 L2 消息选择器契约 ──────────────────────
  // RMR-2026-11-10-01：yuanbao / chatglm 的旧 messageList 在真实会话页
  // 全部 0 命中 ⇒ countGrew 恒 false ⇒ 明明回复已生成却判 Response timeout。
  // 这两条锚守的是「修好的选择器不许再漂回去」。
  {
    name: "把元宝的消息选择器退回 0 命中的旧三件套",
    why: "真机实锤：旧三个选择器在已登录会话页 0 命中，handleWaitForResponse 永远等不到 ready",
    target: "src/platforms/yuanbao-adapter.js",
    find: "    '[data-conv-speaker]',\n",
    replace: "",
    testFile: "real-machine/multi-platform-selector.test.mjs",
    expectTest: "元宝消息气泡能被数出来",
  },
  {
    name: "把智谱的消息选择器退回 0 命中的旧三件套",
    why: "发送期 DOM 采样：.chat-message / [class*=message] / [class*=response] 全程 0 命中，只有 .answer-content-wrap 随回复 0→1→2→3 增长",
    target: "src/platforms/chatglm-adapter.js",
    find: '    ".answer-content-wrap",\n',
    replace: "",
    testFile: "real-machine/multi-platform-selector.test.mjs",
    expectTest: "智谱消息气泡能被数出来",
  },
  {
    name: "把文心的消息选择器退回 0 命中的旧三件套",
    why: "2026-11-11 真机实测：已登录会话页旧三件套 0 命中；只有 div.answer-container 随回复增长（4 轮 = 4 个，文本 66/44/38/32）",
    target: "src/platforms/yiyan-adapter.js",
    find: '    "div.answer-container",\n',
    replace: "",
    testFile: "real-machine/multi-platform-selector.test.mjs",
    expectTest: "文心只数 AI 回复容器，不被 answer 附属元素撑大",
  },
  {
    name: "把 Kimi 的消息选择器退回恒定命中的旧选择器",
    why: "2026-11-11 真机实测：[class*=message] 在本站恒定 2 命中（不是气泡）；只有 .chat-content-item-assistant 每条回复 1 个",
    target: "src/platforms/kimi-adapter.js",
    find: '  messageList: [".chat-content-item-assistant", ".chat-content-item"],\n',
    replace: "  messageList: ['.chat-message', '[class*=\"message\"]'],\n",
    testFile: "real-machine/multi-platform-selector.test.mjs",
    expectTest: "Kimi 只数 assistant 条目，不把用户消息算进来",
  },
  {
    name: "把 LongCat 的消息选择器退回 0 命中的旧三件套",
    why: "2026-11-11 真机实测：.message / [class*=response] / [class*=chat-item] 在已登录会话页 0/0/0 命中，fix2 因此在 step_2 挂了 723.9s（4×180s）",
    target: "src/platforms/longcat-adapter.js",
    find: '  messageList: [".assistant-message", ".v-chat-assistant-message"],\n',
    replace: "  messageList: [\".message\", '[class*=\"response\"]', '[class*=\"chat-item\"]'],\n",
    testFile: "real-machine/multi-platform-selector.test.mjs",
    expectTest: "LongCat 只数 AI 条目，不把 human 气泡算进来",
  },
  {
    name: "把 LongCat 的正文选择器退回把状态行带进来的旧版",
    why: "整卡 textContent 含「已搜到 N 个网页」（比正文多 10 字，足以顶过 50 字闸门）；正文只认 .md-show-container",
    target: "src/platforms/longcat-adapter.js",
    find: '  messageContent: [".md-show-container", ".mt-markdown-body", ".markdown"],\n',
    replace: "  messageContent: ['.prose', '.response-content', '[class*=\"content\"]'],\n",
    testFile: "real-machine/multi-platform-selector.test.mjs",
    expectTest: "LongCat 取到正文而不是「已搜到 N 个网页」状态行",
  },

  // ── 超时语义分流（台账 N21）────────────────────────────────
  //
  // 「超时」和「没发出去」在形状上一模一样，都是一次 throw。旧代码不看语义
  // 就重试 ⇒ 重试把同一句提示词**再发一遍** ⇒ 会话里多一条重复提问。
  // 下面每条变异都还原成这个缺陷的某一个侧面。
  {
    name: "超时被判回可重试（N21 原样复活）",
    why: "判回 RETRY 就会重发同一句提示词——会话里多一条重复提问、AI 再答一遍。旧代码正是这样",
    target: "src/utils/retry-policy.js",
    find: "if (error.code === RESPONSE_TIMEOUT_CODE) return FAILURE_STRATEGY.RESUME_WAIT;",
    replace: "if (error.code === RESPONSE_TIMEOUT_CODE) return FAILURE_STRATEGY.RETRY;",
    testFile: "retry-semantics.test.mjs",
    expectTest: "错误码是 RESPONSE_TIMEOUT ⇒ 只能续等，不能重发",
  },
  {
    name: "执行器不认分流结果，一律重跑这一步",
    why: "这就是修复前的样子：resumeOnly 恒 false ⇒ 超时也走「再跑一遍」= 再发一遍",
    target: "src/background/pack-executor.js",
    find: "const resumeOnly = strategy === FAILURE_STRATEGY.RESUME_WAIT;",
    replace: "const resumeOnly = false;",
    testFile: "retry-semantics.test.mjs",
    expectTest: "超时后 SEND_TO_AI 只发一次，随后是带 baselineCount 的续等",
  },
  {
    name: "续等重新数基准条数",
    why: "回复若在「超时」与「续等开始」之间落地，重新数会把它算进基准 ⇒ countGrew 恒 false ⇒ 白等满一个超时窗口",
    target: "src/utils/retry-policy.js",
    find: "if (Number.isInteger(baselineCount) && baselineCount >= 0) return baselineCount;",
    replace: "if (false) return baselineCount;",
    testFile: "retry-semantics.test.mjs",
    expectTest: "续等要用发送前的基准条数，不许重新数",
  },
  {
    name: "续等的消息里丢掉 baselineCount",
    why: "页面收不到基准就只能就地数，等于上一条变异——但从消息协议这一端断了",
    target: "src/background/pack-executor.js",
    find: "      timeout: step?.config?.timeout,\n      baselineCount,\n",
    replace: "      timeout: step?.config?.timeout,\n",
    testFile: "retry-semantics.test.mjs",
    expectTest: "超时后 SEND_TO_AI 只发一次，随后是带 baselineCount 的续等",
  },
  {
    name: "文案兜底退化成子串包含",
    why: "includes(\"Response timeout\") 会把「Response timeout 之后我换了选择器」也判成超时 ⇒ 明明没发出去却不重试，白等一整个窗口",
    target: "src/utils/retry-policy.js",
    find: "if (LEGACY_TIMEOUT_RE.test(msg)) return FAILURE_STRATEGY.RESUME_WAIT;",
    replace: "if (msg.includes(\"Response timeout\")) return FAILURE_STRATEGY.RESUME_WAIT;",
    testFile: "retry-semantics.test.mjs",
    expectTest: "文案里只是**提到**超时，不算超时（不许用子串包含误判）",
  },
  {
    name: "为了修超时把重试整个关掉",
    why: "输入框没找到这类「没送出去」的失败重试是安全的；关掉重试是过度修正，会把可恢复的失败变成硬失败",
    target: "src/background/pack-executor.js",
    find: "        strategy !== FAILURE_STRATEGY.FAIL && step.retry !== false;",
    replace: "        strategy !== FAILURE_STRATEGY.FAIL && false;",
    testFile: "retry-semantics.test.mjs",
    expectTest: "非超时的失败照样重试（别为了修超时把重试一起废了）",
  },
  {
    name: "广播投递超时也放行重发",
    why: "广播时不知道该让哪个页面续等；放行重发就是「多发一遍」的确定副作用",
    target: "src/background/pack-executor.js",
    find: "if (resumeOnly && execution.targetTabId == null) {",
    replace: "if (false) {",
    testFile: "retry-semantics.test.mjs",
    expectTest: "广播投递遇到超时：宁可失败也不重发",
  },

  // ── 证据路径（台账 N22）────────────────────────────────────
  //
  // 2026-11-11 13:32：预检默认文件名只带日期，同日跑第二遍把 5 站记录
  // 静默覆盖成单站。下面每条变异都还原成「又埋一次 N22」的某个侧面。
  {
    name: "预检路径退回只带日期（N22 原样复活）",
    why: "只带日期 ⇒ 同日不同候选集写到同一路径 ⇒ 后跑的静默覆盖先跑的",
    target: "real-machine/evidence-paths.mjs",
    find: "  return `${evidenceDir}/L2-precheck-${date}.${candidatesSlug(candidates)}.json`;",
    replace: "  return `${evidenceDir}/L2-precheck-${date}.json`;",
    testFile: "real-machine/evidence-paths.test.mjs",
    expectTest: "同日两次不同候选集，不得写同一路径",
  },
  {
    name: "候选集不参与文件名",
    why: "slug 恒为空串 ⇒ 路径里少一段，同样撞成同一个文件名",
    target: "real-machine/evidence-paths.mjs",
    find: '  if (list.length <= MAX_SLUG_ITEMS) return list.join("-");',
    replace: '  if (list.length <= MAX_SLUG_ITEMS) return "";',
    testFile: "real-machine/evidence-paths.test.mjs",
    expectTest: "任意两个不同候选集，路径都必须不同（穷举三个真实组合）",
  },
  {
    name: "候选集不排序（同一组因顺序分成两份文件）",
    why: "不排序的话 chatglm,kimi 与 kimi,chatglm 会算出两个名字，证据目录里堆两份内容一样的文件",
    target: "real-machine/evidence-paths.mjs",
    find: "  ].sort();",
    replace: "  ];",
    testFile: "real-machine/evidence-paths.test.mjs",
    expectTest: "同一组候选集换个顺序，得到同一个路径",
  },
  {
    name: "覆盖已有回执时不吭声",
    why: "这就是 N22 的原始形态——覆盖发生了但没有任何提示，只有事后翻证据才发现少了东西",
    target: "real-machine/evidence-paths.mjs",
    find: "  if (!info) return null;\n  return `覆盖已有回执：${path}（原 ${info.size} B）`;",
    replace: "  if (!info) return null;\n  return null;",
    testFile: "real-machine/evidence-paths.test.mjs",
    expectTest: "文件存在时提示里带路径与原大小",
  },

  // ── Pack 的会话边界（step_8 尾部撞墙的结构修复）────────────
  //
  // deepseek / longcat 在第 8 轮撞墙；同一条 fusion 提示词在全新会话里
  // 21s 就通过 ⇒ 「单会话串行跑完 8 步」是变量。下面每条变异都还原成
  // 「会话边界没生效」的某个侧面。
  {
    name: "执行器忽略 fresh_session（会话边界形同虚设）",
    why: "不看这个声明就等于仍然串在一个会话里跑——长会话继续累积，step_8 继续撞墙，而且现象仍像「平台慢」",
    target: "src/background/pack-executor.js",
    find: "if (step.fresh_session) {",
    replace: "if (false) {",
    testFile: "session-boundary.test.mjs",
    expectTest: "声明 fresh_session ⇒ 先开新会话，再发提示词（同一标签页）",
  },
  {
    name: "strict 模式下开新会话失败照旧把提示词发出去",
    why: "这是最坏的退让：发进旧会话的后果是静默的——答案照样生成，只是又背上全部历史、又在同一位置撞墙",
    target: "src/background/pack-executor.js",
    find: "if (response && response.success === false) {",
    replace: "if (false) {",
    testFile: "session-boundary.test.mjs",
    expectTest: "strict：开新会话失败 ⇒ 一条提示词都不许发，Pack 必须失败",
  },
  {
    name: "广播投递也放行 fresh_session",
    why: "广播时不知道该操作哪个页面；放行就等于向不特定的页面碰运气开新会话",
    target: "src/background/pack-executor.js",
    find: "    const base = { stepId: step.id, mode };\n\n    if (targetTabId === null || targetTabId === undefined) {",
    replace: "    const base = { stepId: step.id, mode };\n\n    if (false) {",
    testFile: "session-boundary.test.mjs",
    expectTest: "广播投递声明 fresh_session ⇒ 明确失败，且不发提示词",
  },
  {
    name: "prefer 降级被记成「成功开过新会话」",
    why: "把 available 恒记为 true 之后，「开了新会话」与「没开成」在回执上长得一模一样——那就又变成一句无法核验的声明（千问 2026-11-11 实测就是 available:false 这条路）",
    // 2026-11-11 修正：最初写的是 `available: result.available !== false` →
    // `available: true`，但那条**是空变异**——同一对象字面量里紧跟 `...result`，
    // 展开在后面会把 available 又覆盖回去，行为一点没变，所以测试照常绿。
    // 要真把它改坏，得让强制值**排在展开之后**。
    find:
      "        available: result.available !== false,\n        ...result,",
    replace: "        ...result,\n        available: true,",
    target: "src/background/pack-executor.js",
    testFile: "session-boundary.test.mjs",
    expectTest: "prefer：开不成也照常发送，但回执里必须留下 available:false",
  },
  {
    name: "执行器丢掉 NEW_SESSION 上报的明细（durationMs 到不了回执）",
    why: "把 ...result 展开删掉，回执里就只剩后台自己编的字段——重置耗时、所用策略、前后消息数全部消失，归因又变回猜",
    target: "src/background/pack-executor.js",
    find: "        ...result,\n      };",
    replace: "      };",
    testFile: "session-boundary.test.mjs",
    expectTest: "NEW_SESSION 上报的 durationMs 原样进回执（重置开销可复核）",
  },
  {
    name: "交付的 Pack 悄悄去掉 fresh_session 声明",
    why: "删掉声明不会报错、不会报警，只是 step_8 又变回「背着前 7 轮上下文」——撞墙会以「平台慢」的样子回来",
    target: "packs/examples/xiaohongshu_knowledge_creator.json",
    find: '        "fresh_session": "prefer",\n',
    replace: "",
    testFile: "session-boundary.test.mjs",
    expectTest: "真实 Pack 的 step_8_output 声明了 fresh_session=prefer",
  },
  // ── 「新对话」入口（N23：5 站覆盖 + 重置耗时）────────────────────
  //
  // 这些变异打的是 src/content/new-session-control.js 与生产 adapter，
  // 对应 tests/new-session-control.test.mjs。-tests 直接引用生产 SELECTORS，
  // 所以「把适配器选择器改坏」也会立刻变红，不必等真机 L2。
  {
    name: "删掉「新建会话」文案（Kimi 的 a.logo 立刻够不着）",
    why: "Kimi 页面里没有「新对话」三个字，只有「新建会话」；删掉这个文案，没声明 newChat 的站点就全部降级",
    target: "src/content/new-session-control.js",
    find: '  "新建会话", //',
    replace: "  //",
    testFile: "new-session-control.test.mjs",
    expectTest: "没有 adapter 声明时，「新建会话」文案也要能兜住 Kimi 的 a.logo",
  },
  {
    name: "隐藏语义兜底被清空（千问永远开不成新会话）",
    why: "千问的入口整条祖先链是 opacity-0 的 hover-reveal 层，可见性判据永远拒绝它；清空这层兜底就退回 available:false",
    target: "src/content/new-session-control.js",
    find:
      'export const HIDDEN_SEMANTIC_SELECTORS = [\n  \'[data-session-switch-target="new-chat"]\',\n  \'[data-testid="sidebar-new-chat"]\',\n];',
    replace: "export const HIDDEN_SEMANTIC_SELECTORS = [];",
    testFile: "new-session-control.test.mjs",
    expectTest: "千问：入口藏在 opacity-0/pointer-events-none 的 hover-reveal 层里，靠语义属性兜底",
  },
  {
    name: "Kimi 的 <a> 不再拦默认跳转（整页导航把内容脚本带走）",
    why: "sendResponse 随文档销毁，后台只会看到一次莫名的「开新会话失败」，而真机上很难和「入口没找到」区分开",
    target: "src/content/new-session-control.js",
    find: '  if (isAnchor) document.addEventListener("click", blockNavigation, true);',
    replace: '  if (false) document.addEventListener("click", blockNavigation, true);',
    testFile: "new-session-control.test.mjs",
    expectTest: "Kimi：a.new-chat-btn 是 <a>，点击时默认跳转必须被拦掉",
  },
  {
    name: "输入区同名诱饵不再排除（点到发送区旁边那个）",
    why: "chatglm 输入框旁还有一处文本同为「新对话」的元素，点它的后果不可预料",
    target: "src/content/new-session-control.js",
    find: "    if (el.closest(COMPOSER_ZONE_SELECTOR)) continue; // 发送区旁边的同名元素不认",
    replace: "    // 输入区排除被删掉了",
    testFile: "new-session-control.test.mjs",
    expectTest: "输入区里的同名诱饵不认",
  },
  {
    name: "回执不再记 durationMs（重置开销又变成猜）",
    why: "整包变快/变慢无法归因给重置，正是因为它的固定开销混在 AI 回答耗时里，回执里看不见",
    target: "src/content/new-session-control.js",
    find: "  const finish = (result) => ({ ...result, durationMs: Date.now() - startedAt });",
    replace: "  const finish = (result) => ({ ...result });",
    testFile: "new-session-control.test.mjs",
    expectTest: "chatglm：div.new-session 不是 button，仍被 adapter-selector 命中并真的清空 12→0",
  },
  {
    name: "点了没生效也报成功（不假装重置这条被拆）",
    why: "最坏的一种谎：消息数没下降，回执却说 available:true，Pack 照样把提示词发进旧会话",
    target: "src/content/new-session-control.js",
    find: '  } catch (error) {\n    return refuse(error.message, "click-no-effect", error.code);',
    replace:
      '  } catch (error) {\n    return finish({ available: true, strategy: found.how, messageCountBefore: before, messageCountAfter: before });',
    testFile: "new-session-control.test.mjs",
    expectTest: "点了没生效：消息数没下降就不能算成功",
  },
  {
    name: "chatglm 的 newChat 选择器被改坏",
    why: "adapter 选择器是精度最高的一层，改坏了就只剩文案兜底，站点改文案时双重失效",
    target: "src/platforms/chatglm-adapter.js",
    find: '  newChat: [".new-session"],',
    replace: '  newChat: [".nonexistent-chatglm"],',
    testFile: "new-session-control.test.mjs",
    expectTest: "chatglm：div.new-session 不是 button，仍被 adapter-selector 命中并真的清空 12→0",
  },
  {
    name: "元宝的 newChat 选择器被改坏",
    why: "元宝用的是 .yb-new-chat-entry__item 且措辞为「新建对话」，第一版完全够不着",
    target: "src/platforms/yuanbao-adapter.js",
    find: '  newChat: [".yb-new-chat-entry__item", ".yb-new-chat-entry"],',
    replace: '  newChat: [".nonexistent-yuanbao"],',
    testFile: "new-session-control.test.mjs",
    expectTest: "元宝：div.yb-new-chat-entry__item 用「新建对话」措辞，仍走 adapter-selector",
  },
  {
    name: "Kimi 的 newChat 选择器被改坏",
    why: "Kimi 没有「新对话」文案，选择器一坏就没有其它层能救",
    target: "src/platforms/kimi-adapter.js",
    find: "    'a.new-chat-btn[data-testid=\"sidebar-new-chat\"]',",
    replace: "    'a.nonexistent-kimi',",
    testFile: "new-session-control.test.mjs",
    expectTest: "Kimi：a.new-chat-btn 是 <a>，点击时默认跳转必须被拦掉",
  },
  {
    name: "文心把恒命中的 [class*=message] 兜底塞回 messageList",
    why: "新 UI 落地页上这 8 个是通知中心，不是气泡：发送前基准取 8、回答落地后改取 div.answer-container 得 1，countGrew = 1 > 8 恒 false ⇒ 明明答完还判超时，续等 4 个窗口共 243.6s",
    target: "src/platforms/yiyan-adapter.js",
    find:
      "    // .cosd-markdown-content > .marklang > p.marklang-paragraph。\n  ],",
    replace:
      "    // .cosd-markdown-content > .marklang > p.marklang-paragraph。\n    '[class*=\"message\"]',\n  ],",
    testFile: "message-list-contract.test.mjs",
    expectTest: "文心落地页：通知中心恒在 8 个，但发送前的气泡基准必须是 0",
  },
  {
    name: "文心的 newChat 选择器被改坏",
    why: "这条此前只有静态 DOM 证据，没有任何一层能发现选择器漂移",
    target: "src/platforms/yiyan-adapter.js",
    find: '  newChat: [".new-dialog-container-plain", ".new-dialog-container"],',
    replace: '  newChat: [".nonexistent-yiyan"],',
    testFile: "new-session-control.test.mjs",
    expectTest: "文心：div.new-dialog-container-plain 走 adapter-selector",
  },
  {
    name: "自足性检查放过一个上游没产出的变量",
    why: "把 {{boundary_notes}} 改成一个没人产出的名字，等于提示词不再自足；开新会话后那个位置会是空的——但答案照样生成，现象只是「内容缺一块」",
    // 必须挑 step_8 提示词里**独有**的片段：replace 只替换首次出现，
    // 若命中 step_7（没声明 fresh_session），自足性检查根本不会看它。
    target: "packs/examples/xiaohongshu_knowledge_creator.json",
    find: "边界：{{boundary_notes}}",
    replace: "边界：{{boundary_notes_v2}}",
    testFile: "session-boundary.test.mjs",
    expectTest: "声明 fresh_session 的步骤，提示词引用的变量必须全部来自上游",
  },
];

/**
 * 跑一个测试文件，解析 TAP 输出里失败/通过的测试名。
 * @param {string} testFileAbs
 * @returns {{failed: string[], passed: string[]}}
 */
function runTests(testFileAbs, cwd) {
  const res = spawnSync(
    process.execPath,
    ["--test", "--test-reporter=tap", testFileAbs],
    { encoding: "utf-8", cwd: cwd || HERE },
  );
  const out = `${res.stdout || ""}\n${res.stderr || ""}`;

  const failed = [];
  const passed = [];
  for (const line of out.split("\n")) {
    // TAP: "not ok 3 - 测试名" / "ok 4 - 测试名"
    const m = line.match(/^(not ok|ok)\s+\d+\s+-\s+(.*)$/);
    if (!m) continue;
    const name = m[2].trim();
    if (m[1] === "not ok") failed.push(name);
    else passed.push(name);
  }
  return { failed, passed };
}

/**
 * 执行全部变异。
 * @returns {number} 退出码
 */
function main() {
  // 只跑某个测试文件对应的锚：改完一处守护后先做秒级预检，
  // 不必把 100+ 条全量变异（十几分钟）跑完才发现「锚是空的」。
  // 用法：MUTATION_TESTFILE=new-session-control.test.mjs node ...
  const onlyTestFile = process.env.MUTATION_TESTFILE || "";
  const mutations = onlyTestFile
    ? MUTATIONS.filter((m) => m.testFile === onlyTestFile)
    : MUTATIONS;
  if (onlyTestFile && mutations.length === 0) {
    console.error(`没有锚指向 ${onlyTestFile}`);
    return 1;
  }
  console.log(
    `=== 变异检查（${mutations.length} 条${onlyTestFile ? ` / 仅 ${onlyTestFile}` : " / 全量"}）===\n`,
  );

  // 1) 造一份临时副本：变异全部发生在副本上，工作区一个字节都不动
  rmSync(TMP_ROOT, { recursive: true, force: true });
  mkdirSync(TMP_ROOT, { recursive: true });
  cpSync(TESTS_ROOT, join(TMP_ROOT, "tests"), {
    recursive: true,
    filter: (src) => !src.includes(`${"node_modules"}`),
  });
  // 生产代码也要进来：2026-10-25 起，变异可以直接打**生产 adapter 源码**。
  //
  // 之前这个脚本只能改 tests/ 下的文件，于是「生产选择器漂移了」这类缺陷
  // 根本没地方验证——守护的只有工具层，不是被守护的那处代码本身。
  //
  // 测试文件通过相对路径 '../../src/platforms/xxx-adapter.js' 引生产代码，
  // 副本放在 chrome-extension/.mutation-tmp/ 下面（不是 /tmp），
  // 于是这个相对路径在副本里正好指向被改坏的副本，jsdom 也仍能向上找到。
  cpSync(join(EXT_ROOT, "src"), join(TMP_ROOT, "src"), {
    recursive: true,
    filter: (src) => !src.includes(`${"node_modules"}`),
  });
  // public/ 也要进来：popup 的接线测试要读 public/popup.html 与 popup.js，
  // 而且「public 下的脚本必须语法正确」那条门禁守的正是这个目录。
  cpSync(join(EXT_ROOT, "public"), join(TMP_ROOT, "public"), {
    recursive: true,
    filter: (src) => !src.includes(`${"node_modules"}`),
  });
  // static-assets.cjs 也要进来：接线测试用它把静态资源复制到临时目录，
  // 核对「代码里 getURL 指到的页面在产物里真的存在」。
  // 少了它，那条测试在副本里会整个加载失败 ⇒ 变异会被**假杀**
  // （「文件加载失败」也会被记成测试失败）——比没有门禁更糟。
  const STATIC_ASSETS = "static-assets.cjs";
  if (existsSync(join(EXT_ROOT, STATIC_ASSETS))) {
    cpSync(join(EXT_ROOT, STATIC_ASSETS), join(TMP_ROOT, STATIC_ASSETS));
  }
  // packs/ 也要进来：接线测试要跑**交付给外部用户的那个**冒烟 Pack。
  // 少了它，测试在副本里会读到工作区的原文件 ⇒ 对它的变异永远杀不死。
  const packsSrc = resolve(EXT_ROOT, "..", "packs");
  if (existsSync(packsSrc)) {
    cpSync(packsSrc, join(TMP_ROOT, "packs"), { recursive: true });
  }
  const COPY_ROOT = join(TMP_ROOT, "tests");

  const survivors = [];
  try {
    for (const m of mutations) {
      // target 以 "src/" 或 "public/" 开头 ⇒ 打生产代码（相对扩展根）；
      // target 指向扩展根下的单个文件（如 static-assets.cjs）或 "packs/" ⇒ 也是生产代码；
      // 否则打 tests/ 下的文件（相对 tests/ 根）
      const targetAbs =
        m.target.startsWith("src/") ||
        m.target.startsWith("public/") ||
        m.target.startsWith("packs/") ||
        m.target === "static-assets.cjs"
          ? join(TMP_ROOT, m.target)
          : join(COPY_ROOT, m.target);
      if (!existsSync(targetAbs)) {
        console.error(`✗ ${m.name}：目标文件不存在 ${m.target}`);
        survivors.push(m);
        continue;
      }
      const original = readFileSync(targetAbs, "utf-8");
      if (!original.includes(m.find)) {
        console.error(`✗ ${m.name}：在 ${m.target} 里找不到待替换片段——变异描述与代码脱节`);
        survivors.push(m);
        continue;
      }

      const backup = `${targetAbs}.mutation-backup`;
      renameSync(targetAbs, backup);
      try {
        writeFileSync(targetAbs, original.replace(m.find, m.replace), "utf-8");
        const { failed } = runTests(join(COPY_ROOT, m.testFile));
        const killed = failed.some((name) => name.includes(m.expectTest));
        if (killed) {
          console.log(`✓ ${m.name}\n    被 ${m.expectTest} 杀死`);
        } else {
          console.log(
            `✗ ${m.name}\n    期望「${m.expectTest}」变红，实际失败：${failed.join(" | ") || "（无）"}`,
          );
          survivors.push(m);
        }
      } finally {
        renameSync(backup, targetAbs);
      }
    }
  } finally {
    rmSync(TMP_ROOT, { recursive: true, force: true });
  }

  console.log("");
  if (survivors.length) {
    console.error(`变异存活 ${survivors.length} 条——守护有洞：`);
    for (const s of survivors) console.error(`  - ${s.name}`);
    return 1;
  }
  console.log(`全部 ${mutations.length} 条变异都被杀死。`);
  return 0;
}

process.exit(main());
