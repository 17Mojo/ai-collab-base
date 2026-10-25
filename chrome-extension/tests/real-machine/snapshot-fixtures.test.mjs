/**
 * 真实 DOM 快照产物守护
 *
 * 快照是**证据**，进了 git 仓库就必须能被机检：
 *   - 每家平台都要有一份记录，**采不到也要写原因**（不然「没采到」会悄悄变成「没人管」）；
 *   - 采到的平台，消息计数模型必须站得住两条不变量；
 *   - 快照 HTML 里的个人信息/令牌必须已经脱敏。
 *
 * 注意这里的边界：**快照是冻结的基线**，它守不住「站点改版」——
 * 站点改版是 L1 探针（打真站）的活。本文件守的是
 * 「我们对真机 DOM 的理解被记录下来了，而且自洽」。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve, join } from "node:path";

import { PLATFORMS } from "../platforms.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const REAL_DIR = join(HERE, "fixtures", "real");

/**
 * 读某平台的快照 sidecar。
 * @param {string} id
 * @returns {object|null}
 */
function readMeta(id) {
  const p = join(REAL_DIR, `${id}.json`);
  if (!existsSync(p)) return null;
  return JSON.parse(readFileSync(p, "utf-8"));
}

test("每家平台都有采集记录（采不到也必须有原因）", () => {
  for (const p of PLATFORMS) {
    const meta = readMeta(p.id);
    assert.ok(meta, `平台 ${p.id} 没有采集记录（先跑 snapshot-capture.mjs）`);
    assert.ok(
      ["captured", "unverified", "capture_failed"].includes(meta.outcome),
      `平台 ${p.id} 的 outcome 非法：${meta.outcome}`,
    );
    if (meta.outcome !== "captured") {
      assert.ok(
        meta.reason && meta.reason.length > 0,
        `平台 ${p.id} 没采到，必须写明原因（outcome=${meta.outcome}）`,
      );
    }
  }
});

test("采到的平台必须有 HTML 快照，没采到的不能有", () => {
  for (const p of PLATFORMS) {
    const meta = readMeta(p.id);
    const htmlPath = join(REAL_DIR, `${p.id}.html`);
    if (meta.outcome === "captured") {
      assert.ok(existsSync(htmlPath), `平台 ${p.id} 判定为 captured 却没有 HTML 快照`);
    } else {
      assert.ok(
        !existsSync(htmlPath),
        `平台 ${p.id} 没采到却留下了 HTML 快照——那不是「没采到」的诚实记录`,
      );
    }
  }
});

test("采到的平台的 HTML 里必须有探针标注", () => {
  for (const p of PLATFORMS) {
    const meta = readMeta(p.id);
    if (meta.outcome !== "captured") continue;
    const html = readFileSync(join(REAL_DIR, `${p.id}.html`), "utf-8");
    assert.ok(
      html.includes('data-probe-role="chat-input"'),
      `平台 ${p.id} 的快照没有 chat-input 标注`,
    );
  }
});

test("采到的平台的消息计数模型必须站得住两条不变量", () => {
  for (const p of PLATFORMS) {
    const meta = readMeta(p.id);
    if (meta.outcome !== "captured") continue;
    const model = meta.messageCountModel;
    assert.ok(model, `平台 ${p.id} 缺少 messageCountModel 判定`);
    assert.equal(
      model.ok,
      true,
      `平台 ${p.id} 的消息计数模型不成立：${model.reason}`,
    );
  }
});

test("采到的平台的空闲态必须是 isTyping=false", () => {
  for (const p of PLATFORMS) {
    const meta = readMeta(p.id);
    if (meta.outcome !== "captured") continue;
    assert.equal(
      meta.isTyping,
      false,
      `平台 ${p.id} 在空闲落地页上 isTyping() 为 ${meta.isTyping}——` +
        `「空闲即不忙」被违反，waitForResponse 会必然超时`,
    );
  }
});

test("快照 HTML 里不得残留未脱敏的个人信息 / 令牌", () => {
  for (const p of PLATFORMS) {
    const meta = readMeta(p.id);
    if (meta.outcome !== "captured") continue;
    const html = readFileSync(join(REAL_DIR, `${p.id}.html`), "utf-8");
    assert.doesNotMatch(html, /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/, `平台 ${p.id} 的快照里有邮箱`);
    assert.doesNotMatch(html, /(?:\+?86[-\s]?)?1[3-9]\d{9}/, `平台 ${p.id} 的快照里有手机号`);
    assert.doesNotMatch(html, /\b[A-Za-z0-9_-]{40,}\b/, `平台 ${p.id} 的快照里有长随机串`);
    assert.doesNotMatch(html, /<script/i, `平台 ${p.id} 的快照里有 script`);
    assert.doesNotMatch(html, /\son[a-z]+=/i, `平台 ${p.id} 的快照里有事件属性`);
  }
});

test("快照不得使用 data-role 命名空间（真实站点自己会用它）", () => {
  for (const p of PLATFORMS) {
    const meta = readMeta(p.id);
    if (meta.outcome !== "captured") continue;
    const html = readFileSync(join(REAL_DIR, `${p.id}.html`), "utf-8");
    const ours = html.match(/data-probe-role=/g) || [];
    assert.ok(ours.length > 0, `平台 ${p.id} 的快照里没有 data-probe-role 标注`);
    // 站点的 data-role 可以存在，但不能是我们写的
    const stripped = html.replace(/data-probe-role="[^"]*"/g, "");
    assert.ok(
      !stripped.includes('data-role="chat-input"') &&
        !stripped.includes('data-role="message"') &&
        !stripped.includes('data-role="send-button"'),
      `平台 ${p.id} 的快照里出现了我们自己的 data-role 标注——应统一用 data-probe-role`,
    );
  }
});

test("快照记录里标注了采集时刻与来源", () => {
  for (const p of PLATFORMS) {
    const meta = readMeta(p.id);
    assert.ok(meta.capturedAt, `平台 ${p.id} 缺少 capturedAt`);
    assert.ok(meta.url, `平台 ${p.id} 缺少 url`);
    assert.equal(meta.sanitized, true, `平台 ${p.id} 的快照没有标记为已脱敏`);
  }
});
