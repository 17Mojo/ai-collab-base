/**
 * 真机**注入链路**探针（只注入、不发送）
 *
 * ## 它回答什么问题
 *
 * 「提示词到底进没进站点的编辑器？」——这件事**光看 DOM 不算数**。
 * 现代富文本编辑器（Slate / ProseMirror / Quill …）把内容存在**框架自己的模型**里，
 * DOM 只是投影：往 DOM 里塞字，站点读到的是「用户没输入」
 * ⇒ **发送按钮保持 disabled** ⇒ 点它等于没点 ⇒ 必然超时。
 *
 * 2026-10-26 真机实测（千问）：execCommand 注入后发送按钮 `disabled` 依旧是
 * `true`；换成模型感知的注入后变成 `false`。
 * 这个差别**在单元测试里能仿真**，但「仿真得对不对」只有真机能回答——
 * 所以这里跑**生产链路**（不是页面里手写的探针）：
 *
 *   service worker → chrome.tabs.sendMessage(INJECT_TEXT)
 *     → 内容脚本（生产 dist 产物）→ injectTextSmart → slate-editor.js
 *       → beforeinput → 站点的编辑器模型 → 发送按钮解禁
 *
 * ## 硬约束
 *
 * 1. **只注入，不发送**：绝不点发送、绝不等待回复、绝不消耗账号额度。
 *    「真实发送」那一层是 L2（人工），见 docs/REAL_MACHINE_REGRESSION.md。
 * 2. **必须显式开启**：`--i-will-inject` 不给就退出——避免有人不知情地
 *    往自己的真实账号页面里写东西。
 * 3. **不登录**：本探针不碰登录态；登录由人自己完成。
 * 4. **不进 CI 硬门禁**：站点改版 ≠ 代码缺陷（与 L1 探针同一条纪律）。
 *
 * 用法：
 *   node tests/real-machine/injection-path-probe.mjs --i-will-inject
 *   node tests/real-machine/injection-path-probe.mjs --i-will-inject --platform=gemini
 *   node tests/real-machine/injection-path-probe.mjs --i-will-inject --out=inj.json
 *   node tests/real-machine/injection-path-probe.mjs --i-will-inject --profile-dir=.rm-profile
 *
 * 退出码：0 = 注入链路全过；1 = 有平台没通过；2 = 探针自身异常。
 */

import { chromium } from "playwright";
import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { PLATFORMS as REGISTERED_PLATFORMS } from "../platforms.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const EXT_ROOT = resolve(HERE, "../..");
const DIST = resolve(EXT_ROOT, "dist");

/** 默认只跑千问：目前只有它有「模型级」判据（Slate 的零宽叶子）。 */
const DEFAULT_PLATFORM = "qianwen";

/** 探针注入的文本。用固定串，避免把账号相关的东西写进站点。 */
const PROBE_TEXT = "注入链路探针文本（不发送）";

/**
 * 解析命令行参数。
 * @param {string[]} argv
 * @returns {object}
 */
function parseArgs(argv) {
  const args = {
    platform: DEFAULT_PLATFORM,
    out: null,
    channel: "chromium",
    profileDir: null,
    headed: false,
    iWillInject: false,
    text: PROBE_TEXT,
  };
  for (const raw of argv) {
    const [key, value = "true"] = raw.replace(/^--/, "").split("=");
    if (key === "platform") args.platform = value;
    else if (key === "out") args.out = value;
    else if (key === "channel") args.channel = value;
    else if (key === "profile-dir") args.profileDir = value;
    else if (key === "text") args.text = value;
    else if (key === "headed") args.headed = true;
    else if (key === "i-will-inject") args.iWillInject = true;
  }
  return args;
}

/**
 * 在页面里读「编辑器模型」的状态。
 *
 * 判据与生产代码（src/platforms/slate-editor.js）一致：
 *   - 零宽叶子还在 ⇒ 模型是空的（文字只在 DOM 里，模型没收）；
 *   - 叶子文本（扣掉占位符与零宽节点）⇒ 模型里的内容。
 *
 * @param {import("playwright").Page} page
 * @returns {Promise<object>}
 */
async function readEditorState(page) {
  return page.evaluate(() => {
    const editor =
      document.querySelector('div[data-slate-editor="true"]') ||
      document.querySelector('[contenteditable="true"]') ||
      document.querySelector("textarea");
    const sendButton =
      document.querySelector('button[data-session-switch-target="send-query"]') ||
      document.querySelector('button[type="submit"]') ||
      document.querySelector('button[class*="send" i]');

    let modelText = "";
    if (editor) {
      for (const leaf of editor.querySelectorAll("[data-slate-leaf]")) {
        for (const node of leaf.childNodes) {
          if (node.nodeType === 3) {
            modelText += node.textContent || "";
            continue;
          }
          if (node.nodeType !== 1) continue;
          if (node.hasAttribute("data-slate-placeholder")) continue;
          if (node.hasAttribute("data-slate-zero-width")) continue;
          modelText += node.textContent || "";
        }
      }
    }

    return {
      editorFound: !!editor,
      editorTag: editor ? editor.tagName : null,
      isSlate: !!(editor && editor.hasAttribute("data-slate-editor")),
      zeroWidthLeafPresent: !!(editor && editor.querySelector("[data-slate-zero-width]")),
      modelText,
      domText: editor ? (editor.textContent || "").trim().slice(0, 120) : null,
      sendButtonFound: !!sendButton,
      sendButtonDisabled: sendButton ? !!sendButton.disabled : null,
    };
  });
}

/**
 * 跑一个平台。
 * @param {object} platform
 * @param {object} args
 * @returns {Promise<object>}
 */
async function probePlatform(platform, args) {
  const context = await chromium.launchPersistentContext(
    args.profileDir || undefined,
    {
      channel: args.channel,
      headless: !args.headed,
      viewport: { width: 1440, height: 900 },
      // Playwright 默认带 --disable-extensions，会把 --load-extension 一起废掉。
      ignoreDefaultArgs: ["--disable-extensions"],
      args: [
        `--disable-extensions-except=${DIST}`,
        `--load-extension=${DIST}`,
      ],
    },
  );

  try {
    let serviceWorker = null;
    const swDeadline = Date.now() + 30000;
    while (Date.now() < swDeadline && !serviceWorker) {
      serviceWorker = context.serviceWorkers()[0] || null;
      if (!serviceWorker) await new Promise((r) => setTimeout(r, 500));
    }
    if (!serviceWorker) {
      return { platform: platform.id, outcome: "probe_error", detail: "没等到扩展 service worker（扩展没装上？）" };
    }

    const page = await context.newPage();
    await page.goto(platform.url, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForTimeout(5000);

    const tabId = await serviceWorker.evaluate(async () => {
      const tabs = await chrome.tabs.query({});
      const t = tabs.find((x) => (x.url || "").length > 0);
      return t ? t.id : null;
    });

    const before = await readEditorState(page);

    // 走生产链路：后台 → 内容脚本 → injectTextSmart。
    const receipt = await serviceWorker.evaluate(
      async ({ id, text }) => {
        try {
          return await chrome.tabs.sendMessage(id, { type: "INJECT_TEXT", text });
        } catch (e) {
          return { success: false, error: String(e.message) };
        }
      },
      { id: tabId, text: args.text },
    );

    await page.waitForTimeout(1200);
    const after = await readEditorState(page);

    // 判定
    let verdict = "pass";
    const problems = [];
    if (!receipt || receipt.success !== true) {
      verdict = "fail";
      problems.push(`生产链路回报失败：${JSON.stringify(receipt)}`);
    }
    if (!after.editorFound) {
      verdict = "fail";
      problems.push("页面上找不到编辑器");
    } else if (after.isSlate) {
      // Slate：模型级判据
      if (after.zeroWidthLeafPresent) {
        verdict = "fail";
        problems.push("零宽叶子还在 ⇒ 模型仍是空的（文字只在 DOM 里）");
      }
      if (after.modelText !== args.text) {
        verdict = "fail";
        problems.push(`模型文本不等于注入的文本：${JSON.stringify(after.modelText)}`);
      }
      if (after.sendButtonDisabled !== false) {
        verdict = "fail";
        problems.push("发送按钮仍是禁用的 ⇒ 点它等于没点");
      }
    } else {
      // 非 Slate：只能证明「DOM 里有字」，证明不了「模型收到了」。
      if (!String(after.domText || "").includes(args.text)) {
        verdict = "fail";
        problems.push(`DOM 里找不到注入的文本：${JSON.stringify(after.domText)}`);
      }
    }

    return {
      platform: platform.id,
      name: platform.name,
      url: platform.url,
      outcome: verdict,
      detail: problems.length ? problems.join("；") : "注入落到编辑器模型，发送按钮解禁",
      modelLevelVerifiable: after.isSlate,
      receipt,
      before,
      after,
    };
  } finally {
    await context.close().catch(() => {});
  }
}

/** 主流程。 */
async function main() {
  const args = parseArgs(process.argv.slice(2));

  if (!args.iWillInject) {
    console.error(
      "本探针会往真实站点的输入框里写一段文字（不发送）。\n" +
        "确认要跑就加 --i-will-inject。",
    );
    process.exit(2);
  }

  const platform = REGISTERED_PLATFORMS.find((p) => p.id === args.platform);
  if (!platform) {
    console.error(`未知平台：${args.platform}`);
    process.exit(2);
  }

  console.log(
    `注入链路探针：${platform.name}（${platform.url}）——只注入，不发送。`,
  );

  const result = await probePlatform(platform, args);
  console.log(JSON.stringify(result, null, 2));

  if (args.out) {
    writeFileSync(
      resolve(process.cwd(), args.out),
      JSON.stringify(
        {
          generatedAt: new Date().toISOString(),
          layer: "injection-path",
          readOnly: false,
          sendsMessages: false,
          platform: platform.id,
          result,
        },
        null,
        2,
      ),
      "utf-8",
    );
    console.log(`证据已写到 ${args.out}`);
  }

  process.exit(result.outcome === "pass" ? 0 : 1);
}

main().catch((e) => {
  console.error("[探针自身异常]", e && e.message ? e.message : e);
  process.exit(2);
});
