/**
 * 预检回执的路径推导与覆盖提示（台账 N22 的守护）
 *
 * ## 要防的是什么
 *
 * 2026-11-11 13:32：为复核 chatglm 单独跑了一次预检，默认文件名是
 * `L2-precheck-${TODAY}.json`——**只带日期**。于是 12:41 那轮 5 站预检
 * 被静默覆盖成单站（11903 B → 2412 B）。没报错、没警告，
 * 只有事后翻证据时才会发现「那天的记录怎么只剩一个站」。
 *
 * 那次能救回纯属侥幸：文件已在提交 52f551a 里。
 *
 * ## 这份测试钉什么
 *
 * 1. **同日两次不同候选集，不得写同一路径**（用户明确要求的收口条件）；
 * 2. 同一组候选集换个顺序，必须得到同一个名字——它们本来就是同一组，
 *    名字不同只会让证据目录里堆出两份内容一样的文件；
 * 3. 候选集为空 / 超长时不许退化成空串或互相撞名；
 * 4. 覆盖提示**只在真的覆盖时说**，不存在的文件不许报「原 0 B」。
 *
 * 用法：node --test tests/real-machine/evidence-paths.test.mjs（run-tests 会自动收）
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  MAX_SLUG_ITEMS,
  candidatesSlug,
  overwriteNotice,
  precheckOutputPath,
} from "./evidence-paths.mjs";

const DIR = "/tmp/evidence";
const DATE = "2026-11-11";

/** 便捷：算某候选集在那天的落盘路径 */
const pathFor = (candidates) =>
  precheckOutputPath({ evidenceDir: DIR, date: DATE, candidates });

// ─────────────────────────────────────────────────────────────────────
// 一、用户明确要求的收口条件
// ─────────────────────────────────────────────────────────────────────

test("同日两次不同候选集，不得写同一路径", () => {
  const fiveSites = ["gemini", "kimi", "longcat", "yiyan", "yuanbao", "chatglm"];
  const oneSite = ["chatglm"];

  const a = pathFor(fiveSites);
  const b = pathFor(oneSite);

  assert.notEqual(
    a,
    b,
    `两个候选集写到同一个 %s ⇒ 后跑的会把先跑的**静默覆盖**（N22 就是这么发生的）。a=${a} b=${b}`,
  );
});

test("任意两个不同候选集，路径都必须不同（穷举三个真实组合）", () => {
  const combos = [
    ["chatglm"],
    ["chatglm", "kimi"],
    ["gemini", "kimi", "longcat", "yiyan", "yuanbao", "chatglm"],
  ];
  const paths = combos.map(pathFor);
  assert.equal(
    new Set(paths).size,
    paths.length,
    `候选集不同但路径撞了：${JSON.stringify(paths)}`,
  );
});

// ─────────────────────────────────────────────────────────────────────
// 二、归一化：同一组不许因为顺序不同而分成两份文件
// ─────────────────────────────────────────────────────────────────────

test("同一组候选集换个顺序，得到同一个路径", () => {
  assert.equal(pathFor(["kimi", "chatglm"]), pathFor(["chatglm", "kimi"]));
});

test("重复项与大小写、空白不影响路径", () => {
  assert.equal(
    pathFor([" ChatGLM ", "chatglm"]),
    pathFor(["chatglm"]),
    "去重与归一化没做的话，同一组会生成两个文件",
  );
});

test("空候选集有确定的名字，不退化成空串", () => {
  assert.equal(candidatesSlug([]), "none");
  assert.equal(candidatesSlug(undefined), "none");
  // 空串不能出现：`L2-precheck-2026-11-11..json` 这种名字在 ls 里几乎看不见
  assert.ok(!pathFor([]).includes(".."), `空候选集算出的路径有双点：${pathFor([])}`);
});

test("候选集超过上限时退化成「项数-短哈希」，且仍然区分不同组合", () => {
  const big = Array.from({ length: MAX_SLUG_ITEMS + 2 }, (_, i) => `p${i}`);
  const slug = candidatesSlug(big);
  assert.match(slug, /^10-[0-9a-f]{8}$/, `超长候选集的 slug 形状不对：${slug}`);

  // 同为 10 项、但内容不同 ⇒ 必须不同名（只看项数就会撞）
  const big2 = [...big.slice(0, 9), "p99"];
  assert.notEqual(candidatesSlug(big), candidatesSlug(big2));
});

test("路径带上日期与 .json 后缀，落在证据目录下", () => {
  const p = pathFor(["chatglm"]);
  assert.equal(p, `${DIR}/L2-precheck-${DATE}.chatglm.json`);
});

test("给了 OUT 就原样使用，不做任何加工", () => {
  const override = "/tmp/elsewhere/my-run.json";
  assert.equal(
    precheckOutputPath({
      evidenceDir: DIR,
      date: DATE,
      candidates: ["chatglm"],
      override,
    }),
    override,
    "显式指定 OUT 时必须照办——那是使用者主动要的路径",
  );
});

// ─────────────────────────────────────────────────────────────────────
// 三、覆盖提示：只在真的覆盖时说
// ─────────────────────────────────────────────────────────────────────

test("文件不存在时不报覆盖（不许出现「原 0 B」这种谎）", () => {
  assert.equal(overwriteNotice("/tmp/nope.json", () => null), null);
});

test("文件存在时提示里带路径与原大小", () => {
  const msg = overwriteNotice("/tmp/old.json", () => ({ size: 2412 }));
  assert.ok(msg, "覆盖已有文件却不吭声，等于又埋一次 N22");
  assert.match(msg, /\/tmp\/old\.json/);
  assert.match(msg, /2412/);
});

test("真实文件系统：写过的文件能报出来，没写过的报不出来", async () => {
  const { mkdtempSync, writeFileSync } = await import("node:fs");
  const { tmpdir } = await import("node:os");
  const { join } = await import("node:path");

  const dir = mkdtempSync(join(tmpdir(), "evidence-paths-"));
  const exist = join(dir, "a.json");
  writeFileSync(exist, "0123456789"); // 10 B

  const msg = overwriteNotice(exist);
  assert.ok(msg, "刚写的文件必须被识别成「已存在」");
  assert.match(msg, /10 B/, `实际提示：${msg}`);

  assert.equal(
    overwriteNotice(join(dir, "b.json")),
    null,
    "不存在的文件不许报警告",
  );
});
