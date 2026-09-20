/**
 * 真实场景 E2E 测试
 * 在真实浏览器中验证各平台适配器的 DOM 选择器和文本注入功能
 *
 * 用法:
 *   node tests/e2e-real-dom.js              # 测试所有可访问平台
 *   node tests/e2e-real-dom.js --kimi       # 只测试 Kimi
 *   node tests/e2e-real-dom.js --qianwen    # 只测试千问
 *   node tests/e2e-real-dom.js --build      # 先构建再测试
 */

const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

// ============================================================================
// 平台测试配置
// ============================================================================

const PLATFORM_TESTS = {
  kimi: {
    name: "Kimi",
    url: "https://kimi.moonshot.cn",
    inputSelector: "div.chat-input-editor",
    editorType: "lexical", // Lexical 编辑器
    test: async (page) => {
      const result = await page.evaluate(() => {
        const input = document.querySelector("div.chat-input-editor");
        if (!input) return { found: false };

        // Lexical 编辑器注入
        if (input.__lexicalEditor) {
          const editor = input.__lexicalEditor;
          try {
            const ns = {
              root: {
                children: [{
                  children: [{ detail: 0, format: 0, mode: "normal", style: "", text: "E2E测试", type: "text", version: 1 }],
                  direction: "ltr", format: "", indent: 0, type: "paragraph", version: 1, textFormat: 0,
                }],
                direction: "ltr", format: "", indent: 0, type: "root", version: 1,
              },
            };
            const s = editor.parseEditorState(JSON.stringify(ns));
            editor.setEditorState(s);
            return { found: true, injected: input.textContent.includes("E2E测试"), method: "lexical" };
          } catch (e) {
            return { found: true, injected: false, method: "lexical_error", error: e.message };
          }
        }

        // 回退到 contenteditable
        input.focus();
        document.execCommand("selectAll", false, null);
        document.execCommand("delete", false, null);
        document.execCommand("insertText", false, "E2E测试");
        if (!input.textContent.includes("E2E测试")) {
          const p = input.querySelector("p");
          if (p) p.textContent = "E2E测试";
          else input.innerHTML = "<p>E2E测试</p>";
        }
        input.dispatchEvent(new Event("input", { bubbles: true }));
        return { found: true, injected: input.textContent.includes("E2E测试"), method: "contenteditable" };
      });
      return result;
    },
  },

  qianwen: {
    name: "千问",
    url: "https://tongyi.aliyun.com/qianwen",
    inputSelector: 'div[contenteditable="true"]',
    editorType: "contenteditable",
    sendButtonSelector: 'button[aria-label*="发送"]',
    test: async (page) => {
      const result = await page.evaluate(() => {
        const input = document.querySelector('div[contenteditable="true"]');
        if (!input) return { found: false };

        input.focus();
        document.execCommand("selectAll", false, null);
        document.execCommand("delete", false, null);
        document.execCommand("insertText", false, "E2E测试");
        if (!input.textContent.includes("E2E测试")) {
          const p = input.querySelector("p");
          if (p) p.textContent = "E2E测试";
          else input.innerHTML = "<p>E2E测试</p>";
        }
        input.dispatchEvent(new Event("input", { bubbles: true }));
        return { found: true, injected: input.textContent.includes("E2E测试"), method: "contenteditable" };
      });
      return result;
    },
  },

  yuanbao: {
    name: "腾讯元宝",
    url: "https://yuanbao.tencent.com/chat",
    inputSelector: "div.ql-editor",
    editorType: "quill", // Quill 编辑器
    test: async (page) => {
      const result = await page.evaluate(() => {
        const input = document.querySelector("div.ql-editor") || document.querySelector('div[contenteditable="true"]');
        if (!input) return { found: false };

        input.focus();
        document.execCommand("selectAll", false, null);
        document.execCommand("delete", false, null);
        document.execCommand("insertText", false, "E2E测试");
        if (!input.textContent.includes("E2E测试")) {
          const p = input.querySelector("p");
          if (p) p.textContent = "E2E测试";
          else input.innerHTML = "<p>E2E测试</p>";
        }
        input.dispatchEvent(new Event("input", { bubbles: true }));
        return { found: true, injected: input.textContent.includes("E2E测试"), method: "contenteditable" };
      });
      return result;
    },
  },

  chatglm: {
    name: "智谱清言",
    url: "https://chatglm.cn",
    inputSelector: "textarea",
    editorType: "textarea",
    test: async (page) => {
      const result = await page.evaluate(() => {
        const input = document.querySelector("textarea");
        if (!input) return { found: false };

        const ns = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value")?.set;
        if (ns) ns.call(input, "E2E测试");
        else input.value = "E2E测试";
        input.dispatchEvent(new Event("input", { bubbles: true }));
        return { found: true, injected: input.value.includes("E2E测试"), method: "textarea" };
      });
      return result;
    },
  },

  gemini: {
    name: "Gemini",
    url: "https://gemini.google.com/app",
    inputSelector: "div.ql-editor",
    editorType: "quill",
    requiresVPN: true,
    test: async (page) => {
      const result = await page.evaluate(() => {
        const input = document.querySelector("div.ql-editor") || document.querySelector('div[contenteditable="true"]');
        if (!input) return { found: false };

        input.focus();
        document.execCommand("selectAll", false, null);
        document.execCommand("delete", false, null);
        document.execCommand("insertText", false, "E2E测试");
        if (!input.textContent.includes("E2E测试")) {
          const p = input.querySelector("p");
          if (p) p.textContent = "E2E测试";
          else input.innerHTML = "<p>E2E测试</p>";
        }
        input.dispatchEvent(new Event("input", { bubbles: true }));
        return { found: true, injected: input.textContent.includes("E2E测试"), method: "contenteditable" };
      });
      return result;
    },
  },

  wenxin: {
    name: "百度文心",
    url: "https://wenxin.baidu.com",
    inputSelector: "textarea.ci-textarea",
    editorType: "textarea",
    test: async (page) => {
      const result = await page.evaluate(() => {
        const input = document.querySelector("textarea.ci-textarea") || document.querySelector("textarea");
        if (!input) return { found: false };

        const ns = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value")?.set;
        if (ns) ns.call(input, "E2E测试");
        else input.value = "E2E测试";
        input.dispatchEvent(new Event("input", { bubbles: true }));
        return { found: true, injected: input.value.includes("E2E测试"), method: "textarea" };
      });
      return result;
    },
  },
};

// ============================================================================
// 构建验证
// ============================================================================

function validateBuild() {
  console.log("━━━ 构建产物验证 ━━━\n");

  const distDir = path.resolve(__dirname, "../dist");
  const checks = [];

  // 检查 dist 目录
  if (!fs.existsSync(distDir)) {
    console.log("  ❌ dist/ 目录不存在，请先运行 node build.js\n");
    return { pass: 0, total: 1 };
  }

  const sw = fs.readFileSync(path.join(distDir, "service-worker.js"), "utf8");
  const cs = fs.readFileSync(path.join(distDir, "content-script.js"), "utf8");
  const manifest = JSON.parse(fs.readFileSync(path.join(distDir, "manifest.json"), "utf8"));

  const tests = [
    { name: "service-worker.js 存在", pass: fs.existsSync(path.join(distDir, "service-worker.js")) },
    { name: "content-script.js 存在", pass: fs.existsSync(path.join(distDir, "content-script.js")) },
    { name: "CS IIFE 格式", pass: cs.startsWith("(function()") },
    { name: "CS 无 ESM import", pass: !cs.match(/import\s+\w+\s+from/) },
    { name: "CS 包含 Lexical 支持", pass: cs.includes("__lexicalEditor") },
    { name: "CS 包含 injectIntoLexical", pass: cs.includes("injectIntoLexical") },
    { name: "SW 包含 DeepSeek 适配器", pass: sw.includes("DeepSeekAdapter") },
    { name: "Manifest content_scripts matches >= 15", pass: manifest.content_scripts[0].matches.length >= 15 },
    { name: "Manifest host_permissions >= 15", pass: manifest.host_permissions.length >= 15 },
  ];

  for (const t of tests) {
    console.log("  " + (t.pass ? "✅" : "❌") + " " + t.name);
    checks.push(t);
  }

  const pass = checks.filter(c => c.pass).length;
  console.log("\n  结果: " + pass + "/" + checks.length);
  return { pass, total: checks.length };
}

// ============================================================================
// DOM 验证
// ============================================================================

async function validateDOM(platformIds) {
  console.log("\n━━━ 真实 DOM 验证 ━━━\n");

  const browser = await chromium.launch({ headless: true });
  const results = [];

  for (const id of platformIds) {
    const config = PLATFORM_TESTS[id];
    if (!config) {
      console.log("  ⚠️  未知平台: " + id);
      continue;
    }

    process.stdout.write("  " + config.name + " (" + config.url + ")... ");

    try {
      const page = await browser.newPage();
      await page.goto(config.url, { waitUntil: "domcontentloaded", timeout: 15000 });
      await page.waitForTimeout(5000);

      const result = await config.test(page);

      if (result.found && result.injected) {
        console.log("✅ " + result.method);
        results.push({ id, name: config.name, status: "pass", method: result.method });
      } else if (result.found && !result.injected) {
        console.log("❌ 注入失败 (" + result.method + ")");
        results.push({ id, name: config.name, status: "inject_fail", method: result.method });
      } else {
        console.log("⚠️  输入框未找到（可能需要登录）");
        results.push({ id, name: config.name, status: "not_found" });
      }

      await page.close();
    } catch (e) {
      const msg = e.message.substring(0, 60);
      if (msg.includes("ERR_CONNECTION") || msg.includes("net::")) {
        console.log("⚠️  网络不可达");
        results.push({ id, name: config.name, status: "network_error" });
      } else {
        console.log("❌ " + msg);
        results.push({ id, name: config.name, status: "error", error: msg });
      }
    }
  }

  await browser.close();

  const pass = results.filter(r => r.status === "pass").length;
  console.log("\n  结果: " + pass + "/" + results.length + " 通过");

  return results;
}

// ============================================================================
// Chrome 扩展加载验证
// ============================================================================

async function validateExtension() {
  console.log("\n━━━ Chrome 扩展加载验证 ━━━\n");

  const extensionPath = path.resolve(__dirname, "../dist");
  const userDataDir = "/tmp/e2e-ext-test-" + Date.now();

  try {
    const context = await chromium.launchPersistentContext(userDataDir, {
      headless: false,
      args: [
        "--disable-extensions-except=" + extensionPath,
        "--load-extension=" + extensionPath,
      ],
    });

    console.log("  ✅ Chrome 已启动，扩展已加载");

    // 打开千问测试
    const page = await context.newPage();
    await page.goto("https://tongyi.aliyun.com/qianwen", { waitUntil: "domcontentloaded", timeout: 15000 });
    await page.waitForTimeout(5000);

    const state = await page.evaluate(() => {
      const input = document.querySelector('div[contenteditable="true"]');
      const sendBtn = document.querySelector('button[aria-label*="发送"]');
      return {
        hasInput: !!input,
        hasSendButton: !!sendBtn,
      };
    });

    console.log("  千问页面: input=" + state.hasInput + ", sendBtn=" + state.hasSendButton);

    // 注入测试
    const injectResult = await page.evaluate(() => {
      const input = document.querySelector('div[contenteditable="true"]');
      if (!input) return { success: false };
      input.focus();
      document.execCommand("selectAll", false, null);
      document.execCommand("delete", false, null);
      document.execCommand("insertText", false, "扩展E2E测试");
      input.dispatchEvent(new Event("input", { bubbles: true }));
      return { success: input.textContent.includes("扩展E2E") };
    });

    console.log("  注入测试: " + (injectResult.success ? "✅" : "❌"));

    await page.screenshot({ path: "/tmp/e2e-extension-test.png" });
    console.log("  截图: /tmp/e2e-extension-test.png");

    await new Promise(r => setTimeout(r, 2000));
    await context.close();

    return { success: state.hasInput && injectResult.success };
  } catch (e) {
    console.log("  ❌ " + e.message.substring(0, 100));
    return { success: false };
  }
}

// ============================================================================
// 主函数
// ============================================================================

async function main() {
  const args = process.argv.slice(2);

  console.log("╔══════════════════════════════════════════════════════╗");
  console.log("║  Chrome Extension 真实场景 E2E 测试                ║");
  console.log("╚══════════════════════════════════════════════════════╝\n");

  // 先构建
  if (args.includes("--build")) {
    console.log("构建中...");
    const { execSync } = require("child_process");
    execSync("node build.js", { cwd: path.resolve(__dirname, ".."), stdio: "inherit" });
    console.log("");
  }

  // 1. 构建验证
  const buildResult = validateBuild();

  // 2. 确定要测试的平台
  const skipFlags = ["--build", "--no-extension"];
  const platformArgs = args.filter(a => a.startsWith("--") && !skipFlags.includes(a));
  const platformIds = platformArgs.length > 0
    ? platformArgs.map(a => a.replace("--", ""))
    : Object.keys(PLATFORM_TESTS);

  // 3. DOM 验证
  const domResults = await validateDOM(platformIds);

  // 4. 扩展加载验证（仅测试千问）
  if (!args.includes("--no-extension")) {
    const extResult = await validateExtension();

    // 总结
    console.log("\n╔══════════════════════════════════════════════════════╗");
    console.log("║  测试总结                                            ║");
    console.log("╚══════════════════════════════════════════════════════╝");
    console.log("  构建产物: " + buildResult.pass + "/" + buildResult.total);
    console.log("  DOM 验证: " + domResults.filter(r => r.status === "pass").length + "/" + domResults.length);
    console.log("  扩展加载: " + (extResult.success ? "✅" : "❌"));

    const allPass = buildResult.pass === buildResult.total
      && domResults.filter(r => r.status === "pass").length > 0
      && extResult.success;

    process.exit(allPass ? 0 : 1);
  } else {
    console.log("\n╔══════════════════════════════════════════════════════╗");
    console.log("║  测试总结                                            ║");
    console.log("╚══════════════════════════════════════════════════════╝");
    console.log("  构建产物: " + buildResult.pass + "/" + buildResult.total);
    console.log("  DOM 验证: " + domResults.filter(r => r.status === "pass").length + "/" + domResults.length);
  }
}

main().catch(err => {
  console.error("测试失败:", err);
  process.exit(1);
});
