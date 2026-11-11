/**
 * 多平台消息选择器契约（2026-11-10 真机实证）
 *
 * 背景：RMR-2026-11-10-01 里 yuanbao / chatglm 的 L2 都判 Response timeout，
 * 但截图显示 prompt 与 AI 回复都已真实渲染。只读 DOM 探针实锤两站旧的
 * messageList 选择器在真实会话页 **0 命中** ⇒ handleWaitForResponse 的
 * countGrew 恒 false ⇒ 永远等不到 ready。
 *
 * 本测试用真机采集到的 DOM 形状（不是凭空编的）钉住两件事：
 *   1. 消息气泡能被数出来，且新回复出现后计数真的会增长；
 *   2. 最新一条能提取到完整正文，不是状态条或流式碎片。
 *
 * 对应的变异锚在 tests/real-machine/mutation-check.mjs：摘掉新选择器，
 * 这两个用例必须变红。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";

import { SELECTORS as YUANBAO } from "../../src/platforms/yuanbao-adapter.js";
import { SELECTORS as CHATGLM } from "../../src/platforms/chatglm-adapter.js";
import { SELECTORS as YIYAN } from "../../src/platforms/yiyan-adapter.js";
import { SELECTORS as KIMI } from "../../src/platforms/kimi-adapter.js";
import { SELECTORS as LONGCAT } from "../../src/platforms/longcat-adapter.js";
import {
  findElements,
  extractMessageContent,
} from "../../src/platforms/adapter-utils.js";

const AI_TEXT =
  "别再把它当成更高级的聊天机器人——它是一套能自己定计划、调工具、改错并交付结果的自主执行系统。";

/** 2026-11-10 真机 DOM 采集：yuanbao 已登录会话的气泡结构。 */
function yuanbaoDom(withAi = true) {
  return `<div id="app">
    <div class="agent-chat__list__item agent-chat__list__item--human"
         data-conv-speaker="human" data-conv-idx="1" data-conv-outputting="false">
      <div class="agent-chat__list__item__content">你要写一条小红书知识图文的开头。主题：AI 智能体到底是什么。</div>
    </div>
    ${withAi ? `<div class="agent-chat__list__item agent-chat__list__item--ai"
         data-conv-speaker="ai" data-conv-idx="2" data-conv-outputting="false">
      <div class="agent-chat__bubble agent-chat__bubble--ai">
        <div class="agent-chat__bubble__content">
          <div class="hyc-content-md hyc-content-md-done">
            <div class="hyc-common-markdown"><div class="ybc-p">${AI_TEXT}</div></div>
          </div>
        </div>
      </div>
    </div>` : ""}
  </div>`;
}

/** 2026-11-10 发送期 DOM 采样：chatglm 的 .answer-content-wrap 0→1→2→3。 */
function chatglmDom(answerCount = 1) {
  const answers = Array.from({ length: answerCount }, (_, i) =>
    `<div class="conversation-item"><div class="conversation answer">
       <div class="answer-content-wrap">${i === 0 ? AI_TEXT : "第 " + (i + 1) + " 条回复正文，内容足够长以便通过长度闸门。"}</div>
     </div></div>`).join("");
  return `<div id="app">
    <div class="conversation-item"><div class="conversation question pr">
      <div class="question-txt">你要写一条小红书知识图文的开头。</div>
    </div></div>
    ${answers}
  </div>`;
}

/** 在临时 jsdom 里跑生产函数（findElements 依赖全局 document）。 */
function inDom(html, fn) {
  const dom = new JSDOM(html);
  const hadDocument = Object.prototype.hasOwnProperty.call(globalThis, "document");
  const prevDocument = globalThis.document;
  const hadWindow = Object.prototype.hasOwnProperty.call(globalThis, "window");
  const prevWindow = globalThis.window;
  globalThis.document = dom.window.document;
  globalThis.window = dom.window;
  try {
    return fn(dom.window.document);
  } finally {
    if (hadDocument) globalThis.document = prevDocument;
    else delete globalThis.document;
    if (hadWindow) globalThis.window = prevWindow;
    else delete globalThis.window;
    dom.window.close();
  }
}

test("元宝消息气泡能被数出来", () => {
  inDom(yuanbaoDom(true), () => {
    const messages = findElements(YUANBAO.messageList);
    assert.equal(messages.length, 2, "应是 1 用户 + 1 AI，不能被界面外壳撑大");
    assert.equal(messages[messages.length - 1].getAttribute("data-conv-speaker"), "ai");
    const content = extractMessageContent(
      messages[messages.length - 1],
      YUANBAO.messageContent,
    );
    assert.ok(content.includes("自主执行系统"), "最新一条要能取到完整正文");
  });
});

test("元宝新回复出现后计数增长", () => {
  inDom(yuanbaoDom(false), (doc) => {
    const before = findElements(YUANBAO.messageList).length;
    assert.equal(before, 1);
    const ai = doc.createElement("div");
    ai.className = "agent-chat__list__item agent-chat__list__item--ai";
    ai.setAttribute("data-conv-speaker", "ai");
    ai.innerHTML = `<div class="agent-chat__bubble__content">
      <div class="hyc-content-md hyc-content-md-done">${AI_TEXT}</div></div>`;
    doc.querySelector("#app").appendChild(ai);
    const after = findElements(YUANBAO.messageList).length;
    assert.ok(after > before, "countGrew 必须成立，否则 waitForResponse 永远超时");
  });
});

test("智谱消息气泡能被数出来", () => {
  inDom(chatglmDom(1), () => {
    const messages = findElements(CHATGLM.messageList);
    assert.equal(messages.length, 1);
    const content = extractMessageContent(messages[0], CHATGLM.messageContent);
    assert.ok(content.includes("自主执行系统"));
  });
});

test("智谱新回复出现后计数增长", () => {
  inDom(chatglmDom(1), (doc) => {
    const before = findElements(CHATGLM.messageList).length;
    const wrap = doc.createElement("div");
    wrap.className = "answer-content-wrap";
    wrap.textContent = "第二条回复正文，内容足够长以便通过长度闸门。";
    doc.querySelector("#app").appendChild(wrap);
    const after = findElements(CHATGLM.messageList).length;
    assert.equal(after, before + 1, "发送期采样实测 0→1→2→3，选择器必须跟着涨");
  });
});

/* ───────────────────────────────────────────────────────────────────────────
 * 2026-11-11 新增：文心一言 / Kimi
 *
 * 真机采集形状见 evidence/L2-{yiyan,kimi}-dom-shape-2026-11-11.json，
 * 命中数见 L2-{yiyan,kimi}-selector-count-2026-11-11.json。
 * 两站旧 messageList 在真实会话页分别 0 命中 / 恒定 2 命中 ⇒ L2 全部 Response timeout。
 * ─────────────────────────────────────────────────────────────────────────── */

/** 2026-11-11 真机采集：文心一言已登录会话（含侧栏历史与 answer 附属元素作干扰项）。 */
function yiyanDom(answerCount = 1) {
  const answers = Array.from(
    { length: answerCount },
    (_, i) => `
    <div class="conversation-flow-answer-container _answer-container_1ozo5_22">
      <div class="answer-container cs-enable-selection _container_ea7rh_1 _answer-history_1ozo5_9">
        <div class="ai-entry">
          <div class="ai-entry-block ai-markdown">
            <div class="cosd-markdown"><div class="cosd-markdown-content"><div class="marklang">
              <p class="marklang-paragraph">${
                i === answerCount - 1
                  ? AI_TEXT
                  : "第 " + (i + 1) + " 条回复正文，足够长以便通过长度闸门。"
              }</p>
            </div></div></div>
          </div>
          <div class="cs-answer-hover-menu-container _menu_1fov1_1"></div>
        </div>
      </div>
    </div>`,
  ).join("");
  return `<div id="app">
    <div class="chat-side-list-item chat-side-list-item-sample selected">
      <span class="history-item-text">你要写一条小红书知识图文的开头。</span>
    </div>
    <div class="conversation-flow-content _scroll-content_1ozo5_34">
      <div class="chat-qa-container cs-rank-container">
        <div class="conversation-flow-question-container _question-container_1ozo5_15">
          <div class="cs-question-bubble cs-bubble">
            <span class="cs-question-pure-text">你要写一条小红书知识图文的开头。主题：AI 智能体（Agent）到底是什么。</span>
          </div>
        </div>
        ${answers}
      </div>
      <div class="history-answer-box"></div>
    </div>
  </div>`;
}

/** 2026-11-11 真机采集：Kimi 已登录会话（assistant 条目内先 toolcall 思考、后正文）。 */
function kimiDom(assistantCount = 1) {
  const items = [];
  for (let i = 0; i < assistantCount; i++) {
    items.push(
      `<div class="chat-content-item chat-content-item-user">
         <div class="markdown">你要写一条小红书知识图文的开头。</div></div>`,
    );
    items.push(
      `<div class="chat-content-item chat-content-item-assistant">
         <div class="toolcall-rollup"><div class="markdown-container toolcall-content-text">
           思考已完成：先把目标拆成动作，再调工具。这段是推理过程，不应被当成答案。
         </div></div>
         <div class="markdown-container"><div class="markdown">${
           i === assistantCount - 1
             ? AI_TEXT
             : "第 " + (i + 1) + " 条回复正文，足够长以便通过长度闸门。"
         }</div></div>
       </div>`,
    );
  }
  return `<div id="app"><div class="chat-content-list">${items.join("")}</div></div>`;
}

test("文心只数 AI 回复容器，不被 answer 附属元素撑大", () => {
  inDom(yiyanDom(4), () => {
    const messages = findElements(YIYAN.messageList);
    assert.equal(messages.length, 4, "4 条 AI 回复 = 4 个 answer-container");
    for (const m of messages) {
      assert.ok(
        m.classList.contains("answer-container"),
        "数出来的必须是 AI 回复容器，不能是 hover 菜单 / 历史条目",
      );
    }
  });
});

test("文心最新一条取到 AI 正文，而不是用户 prompt", () => {
  inDom(yiyanDom(2), () => {
    const messages = findElements(YIYAN.messageList);
    const content = extractMessageContent(
      messages[messages.length - 1],
      YIYAN.messageContent,
    );
    assert.ok(content.includes("自主执行系统"), "必须取到 AI 正文");
    assert.ok(
      !content.includes("你要写一条小红书"),
      "绝不能把用户刚发出去的 prompt 当成 AI 回复（静默错数据）",
    );
  });
});

test("文心新回复出现后计数增长", () => {
  inDom(yiyanDom(1), (doc) => {
    const before = findElements(YIYAN.messageList).length;
    assert.equal(before, 1);
    const wrap = doc.createElement("div");
    wrap.className = "answer-container cs-enable-selection";
    wrap.innerHTML =
      '<div class="ai-entry"><div class="cosd-markdown-content">第二条回复正文，足够长以便通过长度闸门。</div></div>';
    doc.querySelector("#app").appendChild(wrap);
    assert.equal(
      findElements(YIYAN.messageList).length,
      before + 1,
      "真机实测 4 轮 = 4 个 answer-container，计数必须跟着涨",
    );
  });
});

test("Kimi 只数 assistant 条目，不把用户消息算进来", () => {
  inDom(kimiDom(2), () => {
    const messages = findElements(KIMI.messageList);
    assert.equal(messages.length, 2, "2 轮 = 2 个 assistant 条目，user 条目不计");
    for (const m of messages) {
      assert.ok(m.classList.contains("chat-content-item-assistant"));
    }
  });
});

test("Kimi 取到正文而不是 toolcall 思考过程", () => {
  inDom(kimiDom(1), () => {
    const messages = findElements(KIMI.messageList);
    const content = extractMessageContent(messages[0], KIMI.messageContent);
    assert.ok(content.includes("自主执行系统"), "必须取到正文");
    assert.ok(!content.includes("思考已完成"), "不能把思考过程当答案取回");
  });
});

test("Kimi 新回复出现后计数增长", () => {
  inDom(kimiDom(1), (doc) => {
    const before = findElements(KIMI.messageList).length;
    assert.equal(before, 1);
    const item = doc.createElement("div");
    item.className = "chat-content-item chat-content-item-assistant";
    item.innerHTML =
      '<div class="markdown-container"><div class="markdown">第二条回复正文，足够长以便通过长度闸门。</div></div>';
    doc.querySelector(".chat-content-list").appendChild(item);
    assert.equal(findElements(KIMI.messageList).length, before + 1);
  });
});

/* ───────────────────────────────────────────────────────────────────────────
 * 2026-11-11 新增：LongCat
 *
 * 真机采集形状见 evidence/L2-longcat-dom-shape-2026-11-11.fix2.json，
 * 命中数见 L2-longcat-selector-count-2026-11-11.json。
 * 旧三件套 `.message` / `[class*="response"]` / `[class*="chat-item"]`
 * 在已登录会话页 **0 / 0 / 0** 命中 ⇒ fix2 在 step_2 挂了 723.9s（4×180s + 3.9s）。
 *
 * 本站有两个专属陷阱，都在下面钉住：
 *   1. `.assistant-message` 的整卡文本含「已搜到 N 个网页」联网搜索状态行（比正文多 10 字）；
 *   2. 正文容器 `.mt-markdown-body` **永久带 `result-streaming` 类**，回复完成后也不摘。
 * ─────────────────────────────────────────────────────────────────────────── */

const LONGCAT_SEARCH_ROW = "已搜到 14 个网页";

/** 2026-11-11 真机采集：LongCat 已登录会话（含侧栏历史、联网搜索状态行、错误回复）。 */
function longcatDom({ turns = 1, withSearchRow = true, errorReply = false } = {}) {
  const views = [];
  for (let i = 0; i < turns; i++) {
    views.push(
      `<div class="v-chat-messge-view">
         <div class="v-chat-user-message"><div class="user-wrapper"><div class="user-message">
           <div class="user-text">你要写一条小红书知识图文的开头。主题：AI 智能体（Agent）到底是什么。</div>
         </div></div></div>
       </div>`,
    );
    const isLast = i === turns - 1;
    const body = errorReply
      ? `<div class="assistant-message">服务出错啦，请稍后再试试。</div>`
      : `<div class="assistant-message">
           ${withSearchRow ? `<div class="web-search-row">${LONGCAT_SEARCH_ROW}</div>` : ""}
           <div class="md-show-container markdown text-wrap">
             <div class="mt-markdown-body result-streaming">${
               isLast ? AI_TEXT : "第 " + (i + 1) + " 条回复正文，足够长以便通过长度闸门。"
             }</div>
           </div>
         </div>`;
    views.push(
      `<div class="v-chat-messge-view">
         <div class="v-chat-assistant-message"><div class="assistant-main">${body}</div></div>
       </div>`,
    );
  }
  return `<div id="app">
    <div class="conversation-list">
      <div class="conv-item item active"><div class="conv-item-content">
        <div class="conv-title-wrap">它不是工具，而是能自主决策的</div>
      </div></div>
    </div>
    <div class="v-chat-body"><div class="v-message-list">${views.join("")}</div></div>
  </div>`;
}

test("LongCat 只数 AI 条目，不把 human 气泡算进来", () => {
  inDom(longcatDom({ turns: 7 }), () => {
    const messages = findElements(LONGCAT.messageList);
    assert.equal(messages.length, 7, "7 轮 = 7 个 assistant-message，user 气泡与外壳不计");
    for (const m of messages) {
      assert.ok(
        m.classList.contains("assistant-message"),
        "数出来的必须是 AI 条目（混入 human 气泡会让「最新一条」取到用户自己的 prompt）",
      );
    }
  });
});

test("LongCat 取到正文而不是「已搜到 N 个网页」状态行", () => {
  inDom(longcatDom({ turns: 1, withSearchRow: true }), () => {
    const messages = findElements(LONGCAT.messageList);
    const content = extractMessageContent(
      messages[messages.length - 1],
      LONGCAT.messageContent,
    );
    assert.ok(content.includes("自主执行系统"), "必须取到 AI 正文");
    assert.ok(
      !content.includes("已搜到"),
      "联网搜索状态行不能混进正文（整卡 textContent 比正文多这 10 个字）",
    );
    assert.equal(content, AI_TEXT, "取到的应当恰好是 markdown 正文，不多不少");
  });
});

test("LongCat 平台报错回复不冒充答案", () => {
  inDom(longcatDom({ turns: 1, errorReply: true }), () => {
    const messages = findElements(LONGCAT.messageList);
    assert.equal(messages.length, 1, "错误回复也算一条 AI 条目（计数要跟着涨）");
    const content = extractMessageContent(messages[0], LONGCAT.messageContent);
    assert.equal(
      content,
      "",
      "「服务出错啦，请稍后再试试。」没有 markdown 容器 ⇒ 必须返回空串让等待继续，不能当正文交出去",
    );
  });
});

test("LongCat 新回复出现后计数增长", () => {
  inDom(longcatDom({ turns: 1 }), (doc) => {
    const before = findElements(LONGCAT.messageList).length;
    assert.equal(before, 1);
    const view = doc.createElement("div");
    view.className = "v-chat-messge-view";
    view.innerHTML =
      '<div class="v-chat-assistant-message"><div class="assistant-main"><div class="assistant-message">' +
      '<div class="md-show-container"><div class="mt-markdown-body result-streaming">第二条回复正文，足够长以便通过长度闸门。</div></div>' +
      "</div></div></div>";
    doc.querySelector(".v-message-list").appendChild(view);
    assert.equal(
      findElements(LONGCAT.messageList).length,
      before + 1,
      "countGrew 必须成立，否则 waitForResponse 永远超时",
    );
  });
});
