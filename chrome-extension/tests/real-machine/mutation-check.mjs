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
    target: "l2-model.mjs",
    find: "usable[i].messageCount > initial && usable[i].isTyping === false",
    replace: "usable[i].messageCount >= initial && usable[i].isTyping === false",
    testFile: "l2-model.test.mjs",
    expectTest: "生成中解除但计数没涨",
  },
  {
    name: "把「不在生成中」这个条件去掉",
    why: "去掉后等待会在生成中途提前返回——这正是 isTyping 选错时的真实故障模式",
    target: "l2-model.mjs",
    find: "if (usable[i].messageCount > initial && usable[i].isTyping === false) {",
    replace: "if (usable[i].messageCount > initial) {",
    testFile: "l2-model.test.mjs",
    expectTest: "计数涨了但 isTyping 恒为 true",
  },
  {
    name: "基准不再取生产启动那一刻的计数",
    why: "退回用第一个采样做基准，中间落进一条消息就会被误判为「没增长」",
    target: "l2-model.mjs",
    find: "typeof baselineCount === \"number\"",
    replace: "false",
    testFile: "l2-model.test.mjs",
    expectTest: "基准取生产启动那一刻的计数",
  },
  {
    name: "生产取到的正文非空判定恒为真",
    why: "恒为真会让「等待成功但正文是空」这种缺陷被判为通过",
    target: "l2-model.mjs",
    find: "productionContentNonEmpty: Boolean(prodResult && (prodResult.content || \"\").trim().length > 0),",
    replace: "productionContentNonEmpty: true,",
    testFile: "l2-model.test.mjs",
    expectTest: "等待成功但正文是空的",
  },
  {
    name: "证据文件不再脱敏",
    why: "真实会话正文会进 git 仓库，不脱敏等于把个人信息公开",
    target: "l2-model.mjs",
    find: "lastContent: typeof s.lastContent === \"string\" ? sanitizeText(s.lastContent) : \"\",",
    replace: "lastContent: typeof s.lastContent === \"string\" ? s.lastContent : \"\",",
    testFile: "l2-model.test.mjs",
    expectTest: "证据文件里正文被脱敏",
  },
  {
    name: "证据文件谎称脚本发过消息",
    why: "sendsMessages 是给审阅者看的机器可读声明，写错等于伪造证据",
    target: "l2-model.mjs",
    find: "sendsMessages: false,",
    replace: "sendsMessages: true,",
    testFile: "l2-model.test.mjs",
    expectTest: "证据文件里正文被脱敏",
  },
  {
    name: "一致位恒为真",
    why: "一致性是发现「生产结果与时间线对不上」的唯一信号",
    target: "l2-model.mjs",
    find: "consistent: settled === (resolveAtIndex !== null),",
    replace: "consistent: true,",
    testFile: "l2-model.test.mjs",
    expectTest: "生产结果与时间线重放不一致时",
  },
  {
    name: "--i-will-send 闸门失效",
    why: "没有这个闸门，误跑一次就会在真站上发出一条真实消息",
    target: "l2-model.mjs",
    find: "} else if (raw === \"--i-will-send\") {\n      args.iWillSend = true;",
    replace: "} else if (raw === \"--i-will-send\") {\n      args.iWillSend = false;",
    testFile: "l2-model.test.mjs",
    expectTest: "--i-will-send 会打开发送闸门",
  },

  // ── 消息计数模型（两条不变量）────────────────────────────────
  {
    name: "「命中元素必须无文本」这条硬伤判定阈值收紧到永不触发",
    why: "去掉后 Yiyan 的 _chat-container_ 这类界面外壳会被当成消息，计数被撑起来",
    target: "message-model.mjs",
    find: ".filter((x) => (x.textLength ?? 0) > 0)",
    replace: ".filter((x) => (x.textLength ?? 0) > 9999)",
    testFile: "message-model.test.mjs",
    expectTest: "命中界面外壳（Yiyan 的 _chat-container_）",
  },
  {
    name: "去掉「空闲即不忙」这条硬伤判定",
    why: "去掉后 isTyping 恒为 true 的平台会被判为合格，而每次发送都必然超时",
    target: "message-model.mjs",
    find: "if (typing === true) {",
    replace: "if (false) {",
    testFile: "message-model.test.mjs",
    expectTest: "空闲页上 isTyping 为 true",
  },

  // ── 脱敏器 ──────────────────────────────────────────────────
  {
    name: "class 属性重新开始做长随机串脱敏",
    why: "CSS Module 的哈希类名是结构不是令牌，误脱敏会毁掉选择器的命中依据",
    target: "sanitize.mjs",
    find: "if (STRUCTURAL_ATTRS.has(String(name).toLowerCase())) {",
    replace: "if (false) {",
    testFile: "sanitize.test.mjs",
    expectTest: "class 属性不做长随机串脱敏",
  },
  {
    name: "邮箱规则失效",
    why: "真实 DOM 快照要进 git 仓库，邮箱漏出去就是个人信息泄露",
    target: "sanitize.mjs",
    find: "/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}/g",
    replace: "/(?!x)x/g",
    testFile: "sanitize.test.mjs",
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
    testFile: "qianwen-contract.test.mjs",
    expectTest: "消息数只算答案卡",
  },
  {
    name: "把千问的正文选择器退回只取第一段",
    why: "只取 .qk-md-text 只能拿到 markdown 的第一段，多段落答案被截断",
    target: "src/platforms/qianwen-adapter.js",
    find: "    '.qk-markdown',",
    replace: "    '.qk-md-text',",
    testFile: "qianwen-contract.test.mjs",
    expectTest: "答案正文取整个 markdown 容器",
  },
  {
    name: "把千问的发送按钮选择器退回依赖本地化文案",
    why: "aria-label 随界面语言变（站点词典 sendMessage = 发送消息 / 傳送訊息），英文界面下必然落空",
    target: "src/platforms/qianwen-adapter.js",
    find: "    'button[data-session-switch-target=\"send-query\"]',\n",
    replace: "",
    testFile: "qianwen-contract.test.mjs",
    expectTest: "发送按钮靠稳定属性命中",
  },
  {
    name: "把千问的「停止回答」选择器改坏",
    why: "生成中的信号是输入区那个「停止回答」按钮；认不出来就会在回复没写完时提前返回",
    target: "src/platforms/qianwen-adapter.js",
    find: "    'button[aria-label*=\"停止回答\"]',",
    replace: "    'button[aria-label*=\"发送消息\"]',",
    testFile: "qianwen-contract.test.mjs",
    expectTest: "识别停止回答按钮",
  },
  {
    name: "把千问的「接收中卡片」选择器改坏",
    why: "等待首个 token 期间是接收中点点点卡片，它必须能被认成生成中",
    target: "src/platforms/qianwen-adapter.js",
    find: "    'div.answer-receiving-card',",
    replace: "    'div.answer-receiving-card-typo',",
    testFile: "qianwen-contract.test.mjs",
    expectTest: "只有接收中卡片",
  },
  {
    name: "把千问正文的「先看元素自身」这一步去掉",
    why: "markdown 容器与答案卡是同一个元素时，只查后代会漏掉它，退到 .qk-md-text 就只拿到第一段",
    target: "src/platforms/qianwen-adapter.js",
    find: "      const self = element.matches?.(sel) ? element : null;",
    replace: "      const self = null;",
    testFile: "qianwen-contract.test.mjs",
    expectTest: "markdown 容器与答案卡是同一个元素时也能取到完整正文",
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
  const COPY_ROOT = join(TMP_ROOT, "tests");

  const survivors = [];
  try {
    for (const m of MUTATIONS) {
      // target 以 "src/" 开头 ⇒ 打生产代码；否则打 tests/real-machine/ 下的文件
      const targetAbs = m.target.startsWith("src/")
        ? join(TMP_ROOT, m.target)
        : join(COPY_ROOT, "real-machine", m.target);
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
        const { failed } = runTests(join(COPY_ROOT, "real-machine", m.testFile));
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
