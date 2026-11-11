/**
 * 证据文件路径推导 + 覆盖提示（台账 N22）
 *
 * ## 为什么单独抽出来
 *
 * 2026-11-11 13:32 出了一次自伤：为复核 chatglm 单独跑了一次预检，
 * 而预检回执的默认文件名是 `L2-precheck-${TODAY}.json`——**只带日期**。
 * 于是 12:41 那轮 5 站预检被**静默覆盖**成单站（11903 B → 2412 B），
 * 不报错、不警告。那次能救回纯属侥幸（已在提交 52f551a 里）。
 *
 * 这类「同一路径写两次」的缺陷有个共同点：**代码永远不会报错**，
 * 只有事后翻证据时才发现「那天的记录怎么只剩一个站」。
 * 所以把路径推导收成纯函数，能单测、能被变异锚钉住；
 * 而不是埋在脚本里靠人肉记得「跑第二遍要传 OUT」。
 *
 * ## 命名规则
 *
 *   L2-precheck-<date>.<候选集 slug>.json
 *
 * 候选集 slug 对**集合**归一：排序 + 去重 ⇒ `chatglm,kimi` 与
 * `kimi,chatglm` 得到同一个名字（它们本来就是同一组），
 * 但 `chatglm` 与 `chatglm,kimi` 一定不同名。
 * 超过 `MAX_SLUG_ITEMS` 项时退化成「项数-短哈希」——再不退，
 * 6 个平台拼出来的文件名会长到难读，而且继续拼也不增加区分度。
 */

import { createHash } from "node:crypto";
import { statSync } from "node:fs";

/** 超过这么多个候选项就退化成「项数-短哈希」 */
export const MAX_SLUG_ITEMS = 8;

/**
 * 把候选集归一成文件名安全的一段。
 *
 * @param {string[]} candidates - 例如 `["chatglm"]` 或 `["kimi","chatglm"]`
 * @returns {string} 例如 `"chatglm"` / `"chatglm-kimi"` / `"none"`
 */
export function candidatesSlug(candidates) {
  const list = [
    ...new Set(
      (Array.isArray(candidates) ? candidates : [])
        .map((c) => String(c).trim().toLowerCase())
        .filter(Boolean),
    ),
  ].sort();

  if (list.length === 0) return "none";
  if (list.length <= MAX_SLUG_ITEMS) return list.join("-");

  const digest = createHash("sha1")
    .update(list.join(","))
    .digest("hex")
    .slice(0, 8);
  return `${list.length}-${digest}`;
}

/**
 * 预检回执的落盘路径。
 *
 * @param {Object} p
 * @param {string} p.evidenceDir - 证据目录
 * @param {string} p.date - `YYYY-MM-DD`（由调用方给，便于测试固定日期）
 * @param {string[]} p.candidates - 本次预检的候选平台
 * @param {string} [p.override] - `OUT` 环境变量；给了就用，不做任何加工
 * @returns {string}
 */
export function precheckOutputPath({ evidenceDir, date, candidates, override }) {
  if (override) return override;
  return `${evidenceDir}/L2-precheck-${date}.${candidatesSlug(candidates)}.json`;
}

/** 默认的探测：不是普通文件（或不存在）就当作不存在 */
function defaultStat(path) {
  try {
    const st = statSync(path);
    return st.isFile() ? st : null;
  } catch {
    return null;
  }
}

/**
 * 覆盖前的提示文案。**没有覆盖就不返回任何东西**——
 * 日志里不该出现「覆盖了……（原 0 B）」这种对不存在的文件说的话。
 *
 * @param {string} path
 * @param {(path: string) => {size: number}|null} [stat] - 便于测试注入
 * @returns {string|null}
 */
export function overwriteNotice(path, stat = defaultStat) {
  const info = stat(path);
  if (!info) return null;
  return `覆盖已有回执：${path}（原 ${info.size} B）`;
}
