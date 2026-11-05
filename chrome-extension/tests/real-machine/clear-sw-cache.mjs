/**
 * SW ScriptCache 清理器（台账 N15 协议的产品化落点）
 *
 * ## 背景（N15，2026-11-04 实锤）
 *
 * 持久 Chrome profile 的 `Default/Service Worker/ScriptCache/` **按 URL** 缓存
 * SW 脚本：`dist/` 重建后 SW 仍跑旧代码（内容脚本每次注入读盘是新的）——
 * 新旧混跑，闸门静默失效。复跑前必须清三个缓存目录：
 *   `Default/Service Worker`、`Default/Code Cache`、`Default/Extension Scripts`
 *
 * 本模块是这三条路径的**唯一权威来源**：
 *   - `l2-qianwen-auto.mjs` 跑前自动清（import clearSwCaches）；
 *   - 手动加载扩展的人跑本文件 CLI 一条命令清（N15 保持 open 的缺口就是它）。
 *
 * ## 硬红线
 *
 * 1. 只删上面三个**缓存**子目录——登录态（Cookies / Local Storage 等）不在
 *    其中，不受影响；也绝不碰 Default/ 下的其他任何东西（守卫测试盯着）。
 * 2. 路径必须长得像 Chrome profile（存在 `Default/`），否则拒绝执行——
 *    防手滑把任意目录当 profile 传进来。
 * 3. WorkBuddy 沙箱的 safe-delete shim 会拦批量删除（>50 项报确认）。
 *    在 WorkBuddy 环境里跑时如被拦，对该进程设
 *    `CODEBUDDY_SAFE_DELETE_ENABLED=0`（shim 自带开关）；CI / 裸机不受影响。
 *
 * ## 用法
 *
 *   node tests/real-machine/clear-sw-cache.mjs [--dry-run] [profilePath]
 *
 *   profilePath 默认 ~/Library/Application Support/rm-qianwen-l2-profile
 *   （与 l2-qianwen-auto.mjs 同一 profile；勿指回 /tmp——会被系统清）
 */

import { existsSync, readdirSync, rmSync, statSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

/** 要清的三个缓存子目录（相对 profile 下的 Default/）——改这里即全局生效 */
export const CACHE_DIRS = ["Service Worker", "Code Cache", "Extension Scripts"];

export const DEFAULT_PROFILE =
  process.env.PROFILE || `${homedir()}/Library/Application Support/rm-qianwen-l2-profile`;

/**
 * 计算清理计划（纯函数，不碰磁盘删除）。
 *
 * @param {string} profilePath Chrome profile 根目录（其下应有 Default/）
 * @returns {{ok: boolean, targets: string[], reason: string}}
 */
export function planCleanup(profilePath) {
  if (!profilePath || typeof profilePath !== "string") {
    return { ok: false, targets: [], reason: "profile 路径为空" };
  }
  const defaultDir = join(profilePath, "Default");
  if (!existsSync(defaultDir) || !statSync(defaultDir).isDirectory()) {
    return {
      ok: false,
      targets: [],
      reason: `不是 Chrome profile（缺 Default/ 目录）: ${profilePath}`,
    };
  }
  return {
    ok: true,
    targets: CACHE_DIRS.map((d) => join(defaultDir, d)),
    reason: "",
  };
}

function dirSize(dir) {
  let files = 0;
  let bytes = 0;
  const walk = (d) => {
    for (const entry of readdirSync(d, { withFileTypes: true })) {
      const full = join(d, entry.name);
      if (entry.isDirectory()) walk(full);
      else {
        files += 1;
        bytes += statSync(full).size;
      }
    }
  };
  try {
    walk(dir);
  } catch {
    /* 半删/无权限状态按已见部分计 */
  }
  return { files, bytes };
}

/**
 * 执行清理。只删 planCleanup 认可的三个缓存目录；不存在的跳过。
 *
 * @param {string} profilePath
 * @param {{dryRun?: boolean}} [opts]
 * @returns {{ok: boolean, dryRun: boolean, removed: Array<{path: string, files: number, bytes: number}>, skipped: string[], reason: string}}
 */
export function clearSwCaches(profilePath, opts = {}) {
  const dryRun = Boolean(opts.dryRun);
  const plan = planCleanup(profilePath);
  if (!plan.ok) {
    return { ok: false, dryRun, removed: [], skipped: [], reason: plan.reason };
  }
  const removed = [];
  const skipped = [];
  for (const target of plan.targets) {
    if (!existsSync(target)) {
      skipped.push(target);
      continue;
    }
    const size = dirSize(target);
    if (!dryRun) {
      rmSync(target, { recursive: true, force: true });
    }
    removed.push({ path: target, ...size });
  }
  return { ok: true, dryRun, removed, skipped, reason: "" };
}

function main(argv) {
  const dryRun = argv.includes("--dry-run");
  const positional = argv.filter((a) => !a.startsWith("--"));
  const profilePath = positional[0] || DEFAULT_PROFILE;

  const result = clearSwCaches(profilePath, { dryRun });
  if (!result.ok) {
    console.error("拒绝执行:", result.reason);
    return 1;
  }
  const tag = result.dryRun ? "[dry-run] 将删" : "已删";
  for (const r of result.removed) {
    console.log(`${tag}: ${r.path}（${r.files} 文件, ${r.bytes} 字节）`);
  }
  for (const s of result.skipped) {
    console.log(`跳过（不存在）: ${s}`);
  }
  if (result.removed.length === 0) {
    console.log("三个缓存目录都不存在——无需清理。");
  } else if (result.dryRun) {
    console.log("dry-run 结束，未实际删除。去掉 --dry-run 执行。");
  } else {
    console.log("清理完成。重启 Chrome / 重跑自动化即加载新构建。");
  }
  return 0;
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  process.exit(main(process.argv.slice(2)));
}
