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
    name: "把「计数增长」从 > 改成 >=",
    why: "生产口径是严格大于；改成 >= 会把「一条都没多」误判为已回复",
    target: "real-machine/l2-model.mjs",
    find: "usable[i].messageCount > initial && usable[i].isTyping === false",
    replace: "usable[i].messageCount >= initial && usable[i].isTyping === false",
    testFile: "real-machine/l2-model.test.mjs",
    expectTest: "生成中解除但计数没涨",
  },
  {
    name: "把「不在生成中」这个条件去掉",
    why: "去掉后等待会在生成中途提前返回——这正是 isTyping 选错时的真实故障模式",
    target: "real-machine/l2-model.mjs",
    find: "if (usable[i].messageCount > initial && usable[i].isTyping === false) {",
    replace: "if (usable[i].messageCount > initial) {",
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
    expectTest: "等待成功但正文是空的",
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
  {
    name: "把内容脚本的 SEND_TO_AI 分支删掉",
    why: "后台的 AI 步骤靠它才能拿到 AI 的回复；删了 Pack 执行链路就断",
    target: "src/content/content-script.js",
    find:
      '      case "SEND_TO_AI":\n' +
      "        handleSendToAI(message.prompt, message.config?.timeout)\n" +
      "          .then((result) => sendResponse({ success: true, result }))\n" +
      "          .catch((error) =>\n" +
      "            sendResponse({ success: false, error: error.message }),\n" +
      "          );\n" +
      "        return true;\n",
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
      '        const id = pack.metadata?.pack_id || pack.pack_id || pack.id || "";',
    replace: '        const id = pack.id || "";',
    testFile: "extension-wiring.test.mjs",
    expectTest: "popup 渲染出来的 data-id",
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
    find: "      type: 'EXECUTE_PACK',\n      packId,\n      tabId\n",
    replace: "      type: 'EXECUTE_PACK',\n      packId,\n      tabId: null\n",
    testFile: "extension-wiring.test.mjs",
    expectTest: "popup 要把用户当前所在的标签页告诉后台",
  },
  {
    name: "popup 不再打开 Pack 编辑器",
    why: "popup 是外部用户看到的第一屏；没有导入入口就卡在第一步",
    target: "public/popup.js",
    find: "      url: chrome.runtime.getURL('public/pack-editor.html')",
    replace: "      url: 'about:blank'",
    testFile: "extension-wiring.test.mjs",
    expectTest: "popup 必须有「导入 Pack」的入口",
  },
  {
    name: "构建不再复制 public/ 嵌套那份",
    why:
      "代码里 getURL('public/pack-editor.html') 指的是嵌套布局；" +
      "不复制的话那个 URL 在装好的扩展里 404，「导入 Pack」直接断掉",
    target: "static-assets.cjs",
    find: "    copyFileSync(src, resolve(nestedDir, file));\n",
    replace: "",
    testFile: "extension-wiring.test.mjs",
    expectTest: "在构建产物里必须真的存在",
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
  console.log(`=== 变异检查（${MUTATIONS.length} 条）===\n`);

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
    for (const m of MUTATIONS) {
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
  console.log(`全部 ${MUTATIONS.length} 条变异都被杀死。`);
  return 0;
}

process.exit(main());
