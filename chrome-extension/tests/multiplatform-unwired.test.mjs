/**
 * `MultiPlatformExecutor` 的「未接线」状态绊线（台账 N36）
 *
 * ## 为什么要有这份测试
 *
 * 2026-11-18 核查发现：`src/background/multi-platform-executor.js` 里有一套完整的
 * 「同一 prompt 并发注入多个平台」实现，但**没有任何生产入口**——`src/` 全仓 0 个 import、
 * 构建产物 0 命中、popup 没有多平台勾选 UI、service-worker 没有对应消息分支。
 * 也就是说它不是「跑不通」，是「没有入口」。
 *
 * 这类东西的危险不在于坏，在于**它会伪装成现成能力**：
 *   - 读者照 `docs/APPLICATION-EXAMPLES.md` 范例二去找勾选界面，必然落空；
 *   - 维护者可能去修一个从来没人调用的实现；
 *   - 对外宣称「支持多平台 AI 共创」时，无法点按验证。
 *
 * 用户的裁定是「标注未实现」：保留代码（阶段 2/3 是实盘能力，阶段 1 是它的入口，
 * 删掉等于把将来接线的说明书一起扔掉），但在文件头加 `@unwired` 显式标记，
 * 并把文档那一步降级为「规划态」。
 *
 * ## 绊线为什么是双向的
 *
 * 单向检查（「必须带 @unwired」）只能守住「有人偷偷接线」，守不住另一半：
 * 有人删掉标记、说「已经接好了」，但实际上还是没接——那是最糟的状态，
 * 因为它同时失去了诚实标记和真实能力。
 *
 * 所以这里的判据是**标记与现状必须互相印证**：
 *
 *   现状 = 未接线  ⟹  必须带 @unwired，且文档必须写「未接线」
 *   现状 = 已接线  ⟹  必须不带 @unwired，且文档必须不再写「未接线」
 *
 * 两个方向任一处不一致都红。红的含义是「你改了其中一半」，
 * 按文件头「要启用它，必须同时做三件事」补齐即可。
 *
 * ## 为什么用「引用计数」而不是「眼熟的字符串」
 *
 * 「接线」在本仓有多个可观测面：源码 import、service-worker 消息分支、popup UI、
 * 构建产物。任何一面出现都说明它可能真的被用上了，任一面出现都该触发核对。
 * 用 `MultiPlatformExecutor` / `multi-platform-executor` 作为符号名判据，
 * 是因为接线几乎不可能绕过这两个名字（要么 import 路径，要么用类名）。
 *
 * ## 已知局限（故意的，别当成漏检）
 *
 * 1. **文档方向没法由 mutation-check 复现**：`tests/real-machine/mutation-check.mjs`
 *    的临时副本只含 `tests/` `src/` `public/` `packs/`，不含 `docs/`，而本测试读的是
 *    仓库里的真文档。所以「接线了但文档没改」「文档谎称可用」这两个变异是**手工验证**的，
 *    证据在 `known_gaps.json` N36 的 appended_evidence（M3 / M4）。要进自动化，
 *    得先把 `docs/` 纳入副本集。
 * 2. **只看「有没有引用」，不看调用路径通不通**：静态判据能证明「接线了」，
 *    证明不了「点一下真的能跑」。真机点按实证无法被静态检查替代——
 *    本条解除时必须补上，否则只是把死代码换了个更隐蔽的死法。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve, relative } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const EXT_ROOT = resolve(HERE, "..");
const REPO_ROOT = resolve(EXT_ROOT, "..");

/** 实现文件（相对 EXT_ROOT） */
const IMPL_REL = "src/background/multi-platform-executor.js";
const IMPL_ABS = join(EXT_ROOT, IMPL_REL);

/** 文档里描述它的那一节（相对 REPO_ROOT） */
const DOC_REL = "docs/APPLICATION-EXAMPLES.md";
const DOC_ABS = join(REPO_ROOT, DOC_REL);

/** 判定「被引用」的符号名。接线绕不过这两个词。 */
const SYMBOL = "MultiPlatformExecutor";
const MODULE_NAME = "multi-platform-executor";

/**
 * 递归收集目录下的 .js 文件（跳过 node_modules 与点目录）。
 * @param {string} dir
 * @param {string[]} out
 * @returns {string[]}
 */
function collectJs(dir, out = []) {
  if (!existsSync(dir)) return out;
  for (const entry of readdirSync(dir)) {
    if (entry === "node_modules" || entry.startsWith(".")) continue;
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      collectJs(full, out);
    } else if (entry.endsWith(".js") || entry.endsWith(".mjs")) {
      out.push(full);
    }
  }
  return out;
}

/**
 * 把某个文件的注释块剥掉，只留「会被执行到的代码」。
 *
 * 为什么需要：本测试按符号名计数，而 `@unwired` 标记块里**自己就写着**
 * `multi-platform-executor`（说明它是谁）。不剥注释，实现文件永远「命中自己」，
 * 判据必然失真。这里只做够用的处理：整行 `//`、`/* … *\/` 块注释。
 *
 * 局限（已知且够用）：不处理字符串里形如 `//` 的内容。本仓的接线语句
 * （import / 消息分支 / DOM 查询）不会踩到这个边界。
 *
 * @param {string} src
 * @returns {string}
 */
function stripComments(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
}

/**
 * 统计一段文本里对目标的「引用」次数（按行计，便于报错时定位）。
 * @param {string} text
 * @returns {string[]} 命中的行（已 trim）
 */
function hitsIn(text) {
  const out = [];
  for (const line of text.split("\n")) {
    if (line.includes(SYMBOL) || line.includes(MODULE_NAME)) out.push(line.trim());
  }
  return out;
}

/**
 * 采集当前磁盘事实。所有断言共用这一份，避免各测各的口径。
 */
function facts() {
  // ── 1. 实现文件本身：标记在不在 ───────────────────────────────
  const implRaw = readFileSync(IMPL_ABS, "utf8");
  // 判据是「独立的标记行」而不是「文本里出现过 @unwired」：
  // 文件头「启用三件事」那段正文里也引用了一次 `@unwired`，用 includes 会让
  // 「有人删掉标记行、只留正文提及」这种情况仍然被算作「标记在」——
  // 等于绊线在最该响的时候不响。故只认行首的 `* @unwired` 标记行。
  const marked = /^\s*\*\s*@unwired\b/m.test(implRaw);
  // 标记块引用台账编号，是「这条标记有出处」的证据
  const markerCitesLedger = marked && /N36/.test(implRaw.slice(0, implRaw.indexOf("*/\n")));

  // ── 2. 源码侧引用：src/ 下除自身外的命中 ───────────────────────
  const srcRefs = [];
  for (const file of collectJs(join(EXT_ROOT, "src"))) {
    if (resolve(file) === resolve(IMPL_ABS)) continue;
    const code = stripComments(readFileSync(file, "utf8"));
    for (const line of hitsIn(code)) {
      srcRefs.push(`${relative(EXT_ROOT, file)}: ${line}`);
    }
  }

  // ── 3. popup UI：多平台勾选/触发界面 ───────────────────────────
  const popupRefs = [];
  for (const name of ["public/popup.html", "public/popup.js"]) {
    const p = join(EXT_ROOT, name);
    if (!existsSync(p)) continue;
    const code = stripComments(readFileSync(p, "utf8"));
    const uiHits = code
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => /\bexecuteAll\b/.test(l) || l.includes("多平台") || l.includes(MODULE_NAME));
    for (const line of uiHits) popupRefs.push(`${name}: ${line}`);
  }

  // ── 4. 构建产物：未引用模块不会被打进产物 ─────────────────────
  // dist/ 不受跟踪（.gitignore 覆盖），干净检出下不存在 ⇒ 拿不到证据时
  // 明确标成「未探测」，而不是当成「0 命中」蒙混过去。
  const distRefs = [];
  let distProbed = false;
  const distDir = join(EXT_ROOT, "dist");
  if (existsSync(distDir)) {
    for (const file of collectJs(distDir)) {
      distProbed = true;
      const code = stripComments(readFileSync(file, "utf8"));
      for (const line of hitsIn(code)) {
        distRefs.push(`${relative(EXT_ROOT, file)}: ${line.slice(0, 120)}`);
      }
    }
  }

  // ── 5. 文档：范例二那一节怎么说的 ─────────────────────────────
  const doc = readFileSync(DOC_ABS, "utf8");
  const start = doc.indexOf("## 范例二");
  assert.notEqual(start, -1, `文档里找不到「## 范例二」节：${DOC_REL}`);
  const nextHeading = doc.indexOf("\n## 范例三", start);
  const section = doc.slice(start, nextHeading === -1 ? doc.length : nextHeading);
  // 文档对「这一步不可用」的自述用词；一旦接线，这几句就该被删掉
  const docSaysUnwired = section.includes("未接线") || section.includes("无法点按触发");
  const docCitesLedger = section.includes("N36");

  const wired = srcRefs.length > 0 || popupRefs.length > 0 || distRefs.length > 0;
  const evidence = [
    `src/ 引用 ${srcRefs.length} 处`,
    `popup UI ${popupRefs.length} 处`,
    distProbed ? `dist 命中 ${distRefs.length} 处` : "dist 未构建（未探测）",
  ].join(" / ");

  return {
    marked,
    markerCitesLedger,
    srcRefs,
    popupRefs,
    distRefs,
    distProbed,
    docSaysUnwired,
    docCitesLedger,
    wired,
    evidence,
  };
}

test("标记与接线现状必须互相印证（双向绊线）", () => {
  const f = facts();
  if (f.wired) {
    assert.equal(
      f.marked,
      false,
      `代码已经出现生产入口（${f.evidence}），但 ${IMPL_REL} 仍带 @unwired 标记。\n` +
        `「要启用它，必须同时做三件事」只差最后一步：删掉 @unwired，同步改文档与台账 N36。\n` +
        `命中明细：\n  ${[...f.srcRefs, ...f.popupRefs, ...f.distRefs].join("\n  ")}`,
    );
  } else {
    assert.equal(
      f.marked,
      true,
      `${IMPL_REL} 的 @unwired 标记被删了，但没有任何生产入口（${f.evidence}）。\n` +
        `这正是最糟的状态：既没有真实能力，又失去了「读的人一眼知道它没生效」的保护。\n` +
        `要么把它接上，要么把标记加回来。`,
    );
  }
});

test("@unwired 标记必须指明它对应台账 N36", (t) => {
  const f = facts();
  if (f.wired) {
    // 已经接上线了，标记本就不该存在 —— 判据交给上面那条双向绊线，
    // 这里再要求「标记必须带 N36」等于要求人保留一条假标记。
    t.skip("已接线，标记不应存在");
    return;
  }
  assert.equal(
    f.markerCitesLedger,
    true,
    `文件头的 @unwired 标记块必须写明台账编号 N36，否则读者无从追溯「为什么这样就叫未实现」、` +
      `也找不到启用清单。现在标记在，但没有 N36。`,
  );
});

test("未接线时，src/ 里不应出现第二份引用（防止半接线）", (t) => {
  const f = facts();
  if (f.wired) {
    t.skip("已接线，本就不该是零引用");
    return;
  }
  assert.deepEqual(
    f.srcRefs,
    [],
    `期望 src/ 下除实现文件自身外零引用，实际命中：\n  ${f.srcRefs.join("\n  ")}`,
  );
});

test("范例二文档的说法必须与代码现状一致", () => {
  const f = facts();

  assert.equal(
    f.docCitesLedger,
    true,
    `范例二那一节必须提到台账编号 N36，让读者知道这条限制有出处、有后续。`,
  );

  if (f.wired) {
    assert.equal(
      f.docSaysUnwired,
      false,
      `代码已接线（${f.evidence}），但 ${DOC_REL} 范例二仍写着「未接线 / 无法点按触发」。\n` +
        `这些句子现在成了反向误导：读者会以为这功能不能用。请删掉它们并补一句实测状态。`,
    );
  } else {
    assert.equal(
      f.docSaysUnwired,
      true,
      `代码至今没有生产入口（${f.evidence}），但 ${DOC_REL} 范例二没写「未接线 / 无法点按触发」。\n` +
        `读者会照着文档去找「多平台执行模式」的勾选界面，然后找不到。请把〔修订注〕补回来。`,
    );
  }
});
