/**
 * IMPORT_PACKS 的 Pack ID 轨道收口测试
 *
 * ## 这个测试在守什么
 *
 * 此前 service-worker.js 的 `IMPORT_PACKS` 用
 * `pack.metadata?.pack_id || pack.pack_id` 取 id，**两条轨道都放行**；
 * 而 pack-executor.js 的 `loadPack()` 严格只认 `metadata.pack_id`，
 * `replacePacks()` 拿到不合法的包只 `console.warn` 一句就跳过。
 *
 * 于是出现一条用户看不见的断链：
 *   导入报成功 → UI 列得出来 → 点运行必报 "Pack not found"
 * 中间唯一的线索是 console 里一条 warn。
 *
 * 而且 :336 的报错文案写着「缺少 metadata.pack_id」，判据却放行顶层
 * `pack_id` —— 文案与行为自相矛盾。
 *
 * ## 边界
 *
 * 只 stub `chrome.*` 这个**下游依赖**（消息总线 + 存储），
 * `onMessage` 分发、`IMPORT_PACKS` 分支、id 提取判据全部跑真代码。
 *
 * 用法：node --test tests/pack-import-gate.test.mjs
 */

import test from "node:test";
import assert from "node:assert/strict";

/**
 * 装一个最小 chrome 存根，把 onMessage 监听器捕获出来。
 * 存储用内存对象实现 get/set 的语义。
 *
 * 注意：**只装一次**。ES 模块缓存 ⇒ 第二次 `import()` 不会重跑模块体，
 * `addListener` 也就不会再被调用一次。所以这里在模块级 boot，
 * 测试之间只清空 store（node:test 顶层 test 默认串行，不会互相踩）。
 */
const captured = {};
const store = {};

globalThis.chrome = {
  runtime: {
    onInstalled: { addListener(fn) { captured.onInstalled = fn; } },
    onMessage: { addListener(fn) { captured.onMessage = fn; } },
  },
  tabs: { onUpdated: { addListener() {} } },
  storage: {
    onChanged: { addListener() {} },
    local: {
      async get(keys) {
        const out = {};
        for (const k of [].concat(keys || [])) {
          if (k in store) out[k] = store[k];
        }
        return out;
      },
      async set(obj) {
        Object.assign(store, obj);
      },
    },
  },
};

await import("../src/background/service-worker.js");

function resetStore() {
  for (const key of Object.keys(store)) delete store[key];
}

/**
 * 真正要守的不变量：落盘的每个包都必须能被严格判据认出 id。
 *
 * （不写 `store.packs === undefined`：IMPORT_PACKS 无论结果如何都会
 * 最后写一次 `packs`，全部被拒时写的是 `[]` —— 这不是缺陷。）
 */
function assertNoIllegalPacks() {
  const stored = store.packs || [];
  for (const pack of stored) {
    assert.ok(
      pack.metadata && pack.metadata.pack_id,
      `不合法的包不该落进 storage：${JSON.stringify(pack).slice(0, 80)}`,
    );
  }
}

/**
 * 走真消息总线发一条 IMPORT_PACKS，返回 service-worker 的响应。
 * 不替被测函数做任何决定——只把 sendResponse 的异步结果接出来。
 */
function importPacks(captured, payload) {
  return new Promise((resolve) => {
    captured.onMessage(
      {
        type: "IMPORT_PACKS",
        jsonData: typeof payload === "string" ? payload : JSON.stringify(payload),
      },
      {},
      resolve,
    );
  });
}

test("只带顶层 pack_id 的 Pack 必须被拒，且报错指出缺 metadata.pack_id", async () => {
  resetStore();

  const response = await importPacks(captured, {
    pack_id: "backend-only",
    pack_name: "后端形状包",
    version: "2.0",
    pack_data: { workflow: { steps: [] } },
  });

  assert.deepEqual(response.imported, [], "不该有任何包被判定为已导入");
  assert.equal(response.errors.length, 1, "必须有一条可见错误");
  assert.match(
    response.errors[0].error,
    /metadata\.pack_id/,
    "报错必须指向 metadata.pack_id —— 不能文案说 A 判据却认 B",
  );
  assertNoIllegalPacks(store);
});

test("metadata.pack_id 齐全的 Pack 正常导入", async () => {
  resetStore();

  const response = await importPacks(captured, {
    metadata: {
      pack_id: "proper",
      pack_name: "正常包",
      version: "1.0.0",
      type: "creative",
      description: "",
    },
    workflow: { steps: [] },
  });

  assert.deepEqual(response.imported, ["proper"]);
  assert.deepEqual(response.errors, []);
  assert.equal(store.packs.length, 1);
  assert.equal(store.packs[0].metadata.pack_id, "proper");
});

test("metadata 在但 metadata.pack_id 缺失的 Pack 也被拒", async () => {
  resetStore();

  const response = await importPacks(captured, {
    metadata: { pack_name: "忘了写 id", version: "1.0.0" },
    workflow: { steps: [] },
  });

  assert.deepEqual(response.imported, []);
  assert.equal(response.errors.length, 1);
  assert.match(response.errors[0].error, /metadata\.pack_id/);
  assertNoIllegalPacks();
});

test("批量 { packs: [...] } 形状仍可导入，坏包只算自己错", async () => {
  resetStore();

  const response = await importPacks(captured, {
    packs: [
      { metadata: { pack_id: "good", pack_name: "好的", version: "1.0.0", type: "custom" }, workflow: { steps: [] } },
      { pack_id: "top-level-only", pack_name: "坏的", version: "1.0.0", pack_data: { workflow: { steps: [] } } },
    ],
  });

  assert.deepEqual(response.imported, ["good"], "好包照常进");
  assert.equal(response.errors.length, 1, "坏包报自己的错");
  assert.match(response.errors[0].error, /metadata\.pack_id/);
  assert.equal(store.packs.length, 1, "坏包不该落盘");
  assert.equal(store.packs[0].metadata.pack_id, "good");
});
