/**
 * dist 严格一致性（2026-11-12 后续步骤②）
 *
 * 源码绿 ≠ 交付产物绿：真机驱动加载的是 ../../dist，不是 src/。
 * 本脚本只读 dist 两个打包产物，核：
 *   1. sha256 与两次 build 前/后记录一致（由 shell 传入，核幂等）；
 *   2. 本轮新增行为（adapter 级精确文案逃生口）真的进了产物；
 *   3. 上一轮已验证的虚拟列表 / 续等链路没有被新构建抹掉。
 *
 * 输出 JSON 到 stdout，由 gates runner 重定向落盘。
 */
import { readFileSync, statSync } from "node:fs";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const EXT_ROOT = resolve(HERE, "../../../../chrome-extension");
const DIST = resolve(EXT_ROOT, "dist");

const sha256 = (p) => createHash("sha256").update(readFileSync(p)).digest("hex");
const bytes = (p) => statSync(p).size;
const countOf = (text, needle) => text.split(needle).length - 1;

const files = ["dist/content-script.js", "dist/service-worker.js"].map((rel) => {
  const abs = resolve(EXT_ROOT, rel);
  return { rel, abs, sha256: sha256(abs), bytes: bytes(abs), text: readFileSync(abs, "utf-8") };
});

const byRel = Object.fromEntries(files.map((f) => [f.rel, f]));

const CHECKS = [
  {
    name: "内容脚本带本轮新增的 adapter 级文案逃生口策略名",
    file: "dist/content-script.js",
    needle: "adapter-text-match",
    min: 1,
  },
  {
    name: "内容脚本带 deepseek 真入口精确文案",
    file: "dist/content-script.js",
    needle: "开启新对话",
    min: 1,
  },
  {
    name: "内容脚本带 newChatText 声明读取",
    file: "dist/content-script.js",
    needle: "newChatText",
    min: 1,
  },
  {
    name: "内容脚本仍带 longcat 新会话入口选择器",
    file: "dist/content-script.js",
    needle: ".v-slider-header .new-content",
    min: 1,
  },
  {
    name: "内容脚本仍带 longcat 入口 span 兜底",
    file: "dist/content-script.js",
    needle: "div.new-content span",
    min: 1,
  },
  {
    name: "内容脚本仍带内容基准字段（虚拟列表假超时修复）",
    file: "dist/content-script.js",
    needle: "baselineContent",
    min: 1,
  },
  {
    name: "内容脚本仍带虚拟列表白名单站点",
    file: "dist/content-script.js",
    needle: "longcat.ai",
    min: 1,
  },
  {
    name: "内容脚本仍带超时错误码",
    file: "dist/content-script.js",
    needle: "RESPONSE_TIMEOUT",
    min: 1,
  },
  {
    name: "后台产物仍带内容基准透传",
    file: "dist/service-worker.js",
    needle: "baselineContent",
    min: 1,
  },
  {
    name: "后台产物仍带续等无基准保护",
    file: "dist/service-worker.js",
    needle: "RESUME_WAIT_NO_BASELINE",
    min: 1,
  },
];

const keywordChecks = CHECKS.map((c) => {
  const count = countOf(byRel[c.file].text, c.needle);
  return { ...c, count, pass: count >= c.min };
});

const env = process.env;
const csSha = env.CS_SHA || "";
const csSha2 = env.CS_SHA2 || "";
const swSha = env.SW_SHA || "";
const swSha2 = env.SW_SHA2 || "";
const idempotent = env.IDEMPOTENT === "true";
const build2Exit = Number(env.BUILD2 ?? -1);

const hashChecks = [
  {
    path: "dist/content-script.js",
    sha256: byRel["dist/content-script.js"].sha256,
    bytes: byRel["dist/content-script.js"].bytes,
    sha256AfterRebuild: csSha2,
    sameAsFirstBuild: byRel["dist/content-script.js"].sha256 === csSha,
    sameAfterRebuild: byRel["dist/content-script.js"].sha256 === csSha2,
  },
  {
    path: "dist/service-worker.js",
    sha256: byRel["dist/service-worker.js"].sha256,
    bytes: byRel["dist/service-worker.js"].bytes,
    sha256AfterRebuild: swSha2,
    sameAsFirstBuild: byRel["dist/service-worker.js"].sha256 === swSha,
    sameAfterRebuild: byRel["dist/service-worker.js"].sha256 === swSha2,
  },
];

const allPass =
  build2Exit === 0 &&
  idempotent &&
  hashChecks.every((h) => h.sameAsFirstBuild && h.sameAfterRebuild) &&
  keywordChecks.every((k) => k.pass);

console.log(
  JSON.stringify(
    {
      generatedAt: new Date().toISOString(),
      mode: "dist-consistency-deepseek-newchat",
      scope: "2026-11-12 后续步骤②：deepseek adapter 级精确文案逃生口",
      buildLogFirst: "build-2026-11-12.deepseek-newchat.log",
      buildLogSecond: "build-2026-11-12.deepseek-newchat-second.log",
      secondBuildExit: build2Exit,
      idempotent,
      files: hashChecks,
      keywordChecks,
      allPass,
      realMachineVerified: false,
      note: "本证据只核 dist 打包产物；冻结站真机效果未验证，N25 保持 open。",
    },
    null,
    2,
  ),
);

process.exit(allPass ? 0 : 1);
