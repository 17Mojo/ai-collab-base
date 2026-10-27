/**
 * Slate 编辑器的「模型感知」注入。
 *
 * ## 为什么需要单独一套
 *
 * 现代富文本框架（Slate / ProseMirror / Quill …）把内容存在**框架自己的模型**里，
 * DOM 只是模型的投影。2026-10-26 真机实测（千问 qianwen.com）：
 *
 *   - `document.execCommand('insertText')` ⇒ 文字进了 DOM，但 Slate 的模型
 *     **仍然是空的** ⇒ 站点读到「用户没输入」⇒ **发送按钮保持 disabled**
 *     ⇒ 点它等于没点 ⇒ 永远等不到回复。
 *   - 派发 `beforeinput`（inputType=insertText，带 data）⇒ Slate 走它自己的
 *     插入路径 ⇒ 模型收到 ⇒ 零宽叶子消失 ⇒ 发送按钮 `disabled === false`。
 *
 * 这套逻辑**只**对 Slate 生效。其它框架（ProseMirror / Quill）各自的模型
 * 机制不同，本文件对它们**不做任何承诺**，遇到时按原路径走。
 *
 * ## 三条实测出来的约束（缺一不可）
 *
 * 1. **替换语义**：编辑器里已有内容时，只派发 `beforeinput(insertText)` 是
 *    **追加**（旧+新），不是替换。要替换必须先把模型选区变成「全选」。
 * 2. **选区同步是异步的**：DOM 里全选之后，框架要等 `selectionchange` 才会
 *    把选区同步进自己的模型；实测**只等事件不够**，还要再等一个宏任务，
 *    否则删除时模型选区还是折叠的 ⇒ `deleteContentBackward` 只删掉一个字。
 * 3. **判据是结构，不是 textContent**：空编辑器的叶子节点里挂着**占位符**
 *    （千问：「向千问提问」）⇒ 模型的 textContent 永远不为空。
 *    「模型是否为空」只能用**零宽叶子**（`[data-slate-zero-width]`）判断。
 *
 * ## 等待为什么用 setTimeout 而不是 requestAnimationFrame
 *
 * rAF 在**后台标签页里不触发**（Chrome 会暂停后台标签页的渲染）⇒ 用它等待
 * 会让 Pack 流程**永久卡住**（比注入失败更糟）。实测 `setTimeout(0)` 足够。
 */

/** 清空模型的最大重试次数（每次失败只损失末尾一个字符，见 clearSlateModel）。 */
const CLEAR_MAX_ATTEMPTS = 3;

/** 等 selectionchange 的上限；事件不来就按超时走（页面通常已经同步完了）。 */
const SELECTION_SYNC_TIMEOUT_MS = 300;

/** 等模型重渲染（DOM 追上模型）的上限。 */
const MODEL_WAIT_MS = 1500;

/** 等「模型已清空」的判据窗口，比插入短——没清空就该重试而不是干等。 */
const CLEAR_WAIT_MS = 600;

/** 轮询间隔。 */
const POLL_INTERVAL_MS = 50;

/**
 * 判断元素是不是 Slate 编辑区。
 *
 * 判据：编辑区根节点带 `data-slate-editor`，或内部挂着 `data-slate-node`。
 * 千问实测：`div[data-slate-editor="true"][data-slate-node="value"]`。
 *
 * @param {HTMLElement|null} input
 * @returns {boolean}
 */
export function isSlateEditor(input) {
  if (!input) return false;
  if (typeof input.hasAttribute === 'function' && input.hasAttribute('data-slate-editor')) {
    return true;
  }
  if (typeof input.querySelector === 'function') {
    return !!input.querySelector('[data-slate-node]');
  }
  return false;
}

/**
 * 判断 Slate 模型当前是否为空。
 *
 * **结构证据**：模型为空时，那个段落会挂一片零宽叶子
 * （`<span data-slate-zero-width="n" data-slate-length="0">`）；
 * 模型里有文本时，这片叶子不存在。
 *
 * 不能用 textContent 判——占位符（「向千问提问」）是叶子的**子节点**，
 * 模型为空时 textContent 也是「向千问提问」。
 *
 * @param {HTMLElement|null} input
 * @returns {boolean}
 */
export function slateModelIsEmpty(input) {
  if (!input || typeof input.querySelector !== 'function') return true;

  // 一个叶子都没有 ⇒ 模型里没有任何文本节点 ⇒ 空的。
  // （真机上 Slate 总会渲染至少一片叶子；这条兜的是**结构不完整**的
  //  快照/降级渲染，那种情况下确实没有内容可清。）
  if (input.querySelectorAll('[data-slate-leaf]').length === 0) return true;

  const zeroWidth = input.querySelector('[data-slate-zero-width]');
  if (!zeroWidth) return false;
  // data-slate-length 是可选属性；有的话必须是 0 才算空。
  const length = zeroWidth.getAttribute('data-slate-length');
  return length === null || length === '0';
}

/**
 * 读出 Slate 模型当前的全部文本。
 *
 * 叶子节点里的文本可能是裸文本节点，也可能是 `<span data-slate-string="true">`
 * 包裹的文本；两种都要收。**占位符与零宽节点要排除**——它们不是用户输入。
 *
 * 多行提示词实测（千问）：换行是**同一个** `data-slate-string` 文本节点里的
 * `\n`，不是多个叶子 ⇒ 拼起来就是原文，判据「模型文本 == 提示词」成立。
 *
 * @param {HTMLElement|null} input
 * @returns {string}
 */
export function slateModelText(input) {
  if (!input || typeof input.querySelectorAll !== 'function') return '';

  const parts = [];
  for (const leaf of input.querySelectorAll('[data-slate-leaf]')) {
    for (const node of leaf.childNodes) {
      if (node.nodeType === 3) {
        // 裸文本节点
        if (node.textContent) parts.push(node.textContent);
        continue;
      }
      if (node.nodeType !== 1) continue;
      if (node.hasAttribute('data-slate-placeholder')) continue;
      if (node.hasAttribute('data-slate-zero-width')) continue;
      parts.push(node.textContent || '');
    }
  }
  return parts.join('');
}

/**
 * 模型文本是否就是期望的文本。
 *
 * 允许整体 trim 后的相等（容忍站点自己 trim 一下），但**不允许**包含关系——
 * 「旧文字+新提示词」也 contains 新提示词，用 contains 会把**追加**误判成成功。
 *
 * @param {string} modelText
 * @param {string} expected
 * @returns {boolean}
 */
export function slateModelMatches(modelText, expected) {
  if (modelText === expected) return true;
  return modelText.trim() === String(expected).trim();
}

/**
 * 把文本注入 Slate 编辑区（模型感知）。
 *
 * 步骤：
 *   1. 模型非空 ⇒ 先清空：DOM 全选 → 等选区同步进模型 → deleteContentBackward；
 *      判据是零宽叶子回来（没回来就重试，最多 3 次）。
 *   2. beforeinput(insertText) ⇒ 模型收到文本。
 *   3. 判据：模型文本 == 提示词。不成立就**抛错**——宁可报错，
 *      也不要留一个「看起来注入了、其实站点没收到」的假成功。
 *
 * @param {HTMLElement} input - Slate 编辑区
 * @param {string} text - 要注入的文本
 * @returns {Promise<void>}
 */
export async function injectIntoSlateEditor(input, text) {
  if (!input) throw new Error('Slate 编辑区元素不存在');

  const expected = String(text ?? '');

  input.focus();

  if (!slateModelIsEmpty(input)) {
    const cleared = await clearSlateModel(input);
    if (!cleared) {
      throw new Error(
        `清空编辑器模型失败（当前模型内容：${JSON.stringify(
          slateModelText(input).slice(0, 120),
        )}）`,
      );
    }
  }

  dispatchBeforeInput(input, 'insertText', expected);

  const accepted = await waitFor(
    () => slateModelMatches(slateModelText(input), expected),
    MODEL_WAIT_MS,
  );
  if (!accepted) {
    throw new Error(
      `编辑器模型没有接收注入的文本（当前模型内容：${JSON.stringify(
        slateModelText(input).slice(0, 120),
      )}）`,
    );
  }
}

/**
 * 清空 Slate 模型。
 *
 * `deleteContentBackward` 既是操作也是探针：它测的正是「模型选区有没有真的
 * 变成全选」。模型选区没同步好时它只删掉末尾一个字——而这坨内容本来就要
 * 被替换掉，所以这个失败模式是**安全**的。
 *
 * @param {HTMLElement} input
 * @returns {Promise<boolean>} 是否已清空
 */
async function clearSlateModel(input) {
  for (let attempt = 1; attempt <= CLEAR_MAX_ATTEMPTS; attempt++) {
    selectAllContents(input);
    await waitForSelectionChange(SELECTION_SYNC_TIMEOUT_MS);
    // 选区同步进模型之后还要再等一个宏任务，否则模型选区仍是折叠的。
    await nextTask();

    dispatchBeforeInput(input, 'deleteContentBackward', null);

    if (await waitFor(() => slateModelIsEmpty(input), CLEAR_WAIT_MS)) {
      return true;
    }
  }
  return false;
}

/**
 * 在 DOM 里全选编辑区内容。
 *
 * 全选的是 **DOM 选区**——它要等框架自己同步进模型才有意义
 * （见 clearSlateModel 的说明）。
 *
 * @param {HTMLElement} input
 * @returns {boolean} 是否成功设置选区
 */
function selectAllContents(input) {
  const selection =
    typeof window !== 'undefined' && window.getSelection
      ? window.getSelection()
      : null;
  if (!selection) return false;

  try {
    selection.removeAllRanges();
    const range = document.createRange();
    range.selectNodeContents(input);
    selection.addRange(range);
    return true;
  } catch {
    return false;
  }
}

/**
 * 等一次 selectionchange（带超时兜底）。
 *
 * 事件不来（框架没监听、或事件在别的文档上）时按超时返回——
 * 300ms 之后框架通常已经同步完了。
 *
 * @param {number} timeoutMs
 * @returns {Promise<void>}
 */
function waitForSelectionChange(timeoutMs) {
  return new Promise((resolve) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      resolve();
    };
    try {
      document.addEventListener('selectionchange', finish, { once: true });
    } catch {
      // 极端环境下没有 addEventListener：直接按超时走
    }
    setTimeout(finish, timeoutMs);
  });
}

/**
 * 派发 beforeinput 事件。
 *
 * 用 `InputEvent`（不是普通 `Event`）是因为框架要读 `inputType` 和 `data`
 * 两个属性。事件是**合成**的，不会触发浏览器的默认插入——默认插入只有
 * 真实键入/粘贴才有。要让模型收到内容，**必须**是框架自己在
 * `beforeinput` 处理器里写模型。
 *
 * @param {HTMLElement} input
 * @param {string} inputType - insertText / deleteContentBackward …
 * @param {string|null} data
 * @returns {Event}
 */
function dispatchBeforeInput(input, inputType, data) {
  let event;
  try {
    event = new InputEvent('beforeinput', {
      inputType,
      data,
      bubbles: true,
      cancelable: true,
    });
  } catch {
    // 老浏览器没有 InputEvent 构造器：退化成普通事件（框架多半读不到，
    // 但至少不会让整个注入流程崩在这里）。
    event = new Event('beforeinput', { bubbles: true, cancelable: true });
    try {
      event.inputType = inputType;
      event.data = data;
    } catch {
      // 只读属性，忽略
    }
  }
  input.dispatchEvent(event);
  return event;
}

/**
 * 轮询等待某个条件成立。
 *
 * @param {() => boolean} predicate
 * @param {number} timeoutMs
 * @returns {Promise<boolean>} 是否在超时前成立
 */
function waitFor(predicate, timeoutMs) {
  return new Promise((resolve) => {
    if (predicate()) {
      resolve(true);
      return;
    }
    const deadline = Date.now() + timeoutMs;
    const tick = () => {
      if (predicate()) {
        resolve(true);
        return;
      }
      if (Date.now() >= deadline) {
        resolve(false);
        return;
      }
      setTimeout(tick, POLL_INTERVAL_MS);
    };
    setTimeout(tick, POLL_INTERVAL_MS);
  });
}

/**
 * 等一个宏任务。
 *
 * 不用 requestAnimationFrame：后台标签页里 rAF 不触发，会把流程卡死。
 *
 * @returns {Promise<void>}
 */
function nextTask() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}
