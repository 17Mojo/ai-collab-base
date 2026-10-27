/**
 * Slate 站点的「行为」仿真 —— 给静态 fixture 补上模型语义。
 *
 * ## 为什么需要它
 *
 * 静态 fixture（手写 mock 与真机 DOM 快照）只有**结构**，没有**行为**。
 * 而 Slate 编辑器的关键语义恰恰是行为：
 *
 *   - 内容存在**框架自己的模型**里，DOM 只是投影；
 *   - 模型只认 `beforeinput`（execCommand 改 DOM，模型看不见）；
 *   - DOM 选区要等 `selectionchange` 才同步进模型
 *     （这正是「全选后立刻删除只删一个字」的原因）。
 *
 * 2026-10-26 真机实测（千问 www.qianwen.com）确认了这三条。
 *
 * 以前生产代码只往 DOM 里塞字，fixture 照样「通过」——因为
 * 「DOM 里有字」和「模型收到了」是两件事，而**假 fixture 只测前者**。
 * 现在生产代码会校验「模型真的收到了」，fixture 就必须**像真站点一样**：
 * 本模块负责扮演站点，判定一律仍由生产代码给出。
 *
 * ## 仿真的三条行为（都来自真机观察）
 *
 *   1. **模型是事实源**：DOM 由模型渲染；发送按钮的 disabled 读模型；
 *   2. **只有 beforeinput 能改模型**：execCommand 之类手段模型看不见；
 *   3. **选区异步同步**：DOM 选区变化后，等 selectionchange 才写进模型。
 */

/**
 * 给一个 Slate 编辑区装上站点行为。
 *
 * @param {Window} window - jsdom window
 * @param {Element} editor - Slate 编辑区元素
 * @param {object} [options]
 * @param {boolean} [options.acceptBeforeInput=true] - false = 假装站点不处理 beforeinput
 * @param {Element|null} [options.sendButton] - 站点按模型内容解禁的发送按钮
 * @returns {{model: object, type: Function, render: Function}|null}
 */
export function installSlateSiteBehavior(window, editor, options = {}) {
  if (!editor) return null;

  const { document } = window;
  const acceptBeforeInput = options.acceptBeforeInput !== false;
  const sendButton = options.sendButton || null;
  const placeholderText =
    editor.getAttribute("data-placeholder") || "向千问提问";

  /** 框架自己的模型（事实源）。 */
  const model = { text: "", selection: null, events: [] };

  /** 把 DOM 选区换算成模型里的字符偏移。 */
  function domOffset(container, offset) {
    const pre = document.createRange();
    pre.selectNodeContents(editor);
    try {
      pre.setEnd(container, offset);
    } catch {
      return 0;
    }
    return pre.toString().length;
  }

  /** 把 DOM 选区同步进模型（真机里这一步由 selectionchange 驱动）。 */
  function syncSelectionFromDom() {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;
    const range = selection.getRangeAt(0);
    if (
      !editor.contains(range.startContainer) ||
      !editor.contains(range.endContainer)
    ) {
      return;
    }
    const start = Math.min(
      domOffset(range.startContainer, range.startOffset),
      model.text.length,
    );
    const end = Math.min(
      domOffset(range.endContainer, range.endOffset),
      model.text.length,
    );
    model.selection = {
      start: Math.min(start, end),
      end: Math.max(start, end),
    };
  }

  /** 把模型选区写回 DOM（模型变了、DOM 重新渲染后要重新落位）。 */
  function applySelectionToDom() {
    const stringEl = editor.querySelector("[data-slate-string]");
    if (!stringEl || !stringEl.firstChild) return;
    const node = stringEl.firstChild;
    const offset = Math.min(
      model.selection ? model.selection.start : 0,
      node.textContent.length,
    );
    const range = document.createRange();
    range.setStart(node, offset);
    range.collapse(true);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
  }

  /** 由模型重新渲染 DOM（真机里这一步是框架的 re-render）。 */
  function render() {
    editor.innerHTML = "";
    const paragraph = document.createElement("p");
    paragraph.setAttribute("data-slate-node", "element");
    const text = document.createElement("span");
    text.setAttribute("data-slate-node", "text");
    const leaf = document.createElement("span");
    leaf.setAttribute("data-slate-leaf", "true");

    if (model.text === "") {
      const zeroWidth = document.createElement("span");
      zeroWidth.setAttribute("data-slate-zero-width", "n");
      zeroWidth.setAttribute("data-slate-length", "0");
      leaf.appendChild(zeroWidth);
      const placeholder = document.createElement("span");
      placeholder.setAttribute("data-slate-placeholder", "true");
      placeholder.setAttribute("contenteditable", "false");
      placeholder.textContent = placeholderText;
      leaf.appendChild(placeholder);
    } else {
      const string = document.createElement("span");
      string.setAttribute("data-slate-string", "true");
      string.textContent = model.text;
      leaf.appendChild(string);
    }

    text.appendChild(leaf);
    paragraph.appendChild(text);
    editor.appendChild(paragraph);

    // 发送按钮读**模型**，不是读 DOM。
    if (sendButton) sendButton.disabled = model.text === "";

    applySelectionToDom();
  }

  if (acceptBeforeInput) {
    editor.addEventListener("beforeinput", (event) => {
      model.events.push({ inputType: event.inputType, data: event.data });

      if (event.inputType === "insertText" && event.data) {
        event.preventDefault();
        const sel = model.selection ?? {
          start: model.text.length,
          end: model.text.length,
        };
        model.text =
          model.text.slice(0, sel.start) +
          event.data +
          model.text.slice(sel.end);
        model.selection = {
          start: sel.start + event.data.length,
          end: sel.start + event.data.length,
        };
        render();
        return;
      }

      if (event.inputType === "deleteContentBackward") {
        event.preventDefault();
        const sel = model.selection ?? {
          start: model.text.length,
          end: model.text.length,
        };
        if (sel.start !== sel.end) {
          model.text = model.text.slice(0, sel.start) + model.text.slice(sel.end);
        } else if (sel.start > 0) {
          model.text =
            model.text.slice(0, sel.start - 1) + model.text.slice(sel.start);
          sel.start -= 1;
          sel.end -= 1;
        }
        model.selection = { start: sel.start, end: sel.start };
        render();
      }
    });
  }

  // 框架靠 selectionchange 把 DOM 选区同步进模型。
  document.addEventListener("selectionchange", syncSelectionFromDom);

  render();

  return {
    model,
    render,
    /** 像真人一样先在编辑区里打字（走模型的正常插入路径）。 */
    type(text) {
      editor.dispatchEvent(
        new window.InputEvent("beforeinput", {
          inputType: "insertText",
          data: text,
          bubbles: true,
          cancelable: true,
        }),
      );
    },
  };
}

/**
 * 若这个元素是 Slate 编辑区，就给它装上站点行为；不是就什么都不做。
 *
 * @param {Window} window
 * @param {Element|null} editor
 * @param {object} [options]
 * @returns {{model: object, type: Function}|null}
 */
export function installSlateSiteIfNeeded(window, editor, options = {}) {
  if (!editor) return null;
  const isSlate =
    (typeof editor.hasAttribute === "function" &&
      editor.hasAttribute("data-slate-editor")) ||
    (typeof editor.querySelector === "function" &&
      !!editor.querySelector("[data-slate-node]"));
  if (!isSlate) return null;
  return installSlateSiteBehavior(window, editor, options);
}
