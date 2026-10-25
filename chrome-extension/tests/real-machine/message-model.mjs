/**
 * 消息计数模型判定（纯函数，无浏览器依赖）
 *
 * 单独成模块的原因只有一个：**能进单测**。
 * 这个判定是本工单里最有价值的机检断言，而断言必须能被单独验证——
 * 藏在采集脚本里就只能靠人眼看输出。
 *
 * ## 两条不变量
 *
 * **不变量 1（消息）**：落地页（没有会话）上，messageList 选择器命中的元素
 * 必须**全部是空的**——整棵子树没有文字。
 *
 * 为什么要这样讲，而不是「消息数必须是 0」：
 *   - 消息气泡**永远不是空的**，所以「空容器」不可能是气泡；
 *   - 但空容器**不一定是缺陷**：Kimi 的 `message-list-container` 在落地页
 *     就是个空列表容器，它把计数抬高了，但**增长检测依然可用**
 *     （发出消息后容器里多出气泡，计数从 2 变成 3）；
 *   - 真正致命的是命中了**有内容的界面元素**：Yiyan 的 `_chat-container_`
 *     （装着侧边栏 + 顶栏）、Yuanbao 的 `yb-new-chat-entry`（「新建对话」按钮）。
 *     那些是界面外壳，不是消息。
 *
 * 2026-10-25 真机实测抓到的实例：
 *   - Yiyan `[class*="chat"]` 命中 37 个——`body.cos-chat` / `_chat-container_` /
 *     `_chat-container-body_` / `history-chat-*`，全是**有内容的外壳**；
 *   - Yuanbao `[class*="chat"]` 命中 8 个——`yb-new-chat-entry`（按钮）、svg。
 *
 * 这两家的计数因此是**被界面元素撑起来的**，waitForResponse 拿它做
 * 「发送前后比较」，于是要么把导航元素当成 AI 回复返回，要么等不到变化而超时。
 *
 * **不变量 2（忙闲）**：空闲落地页上 isTyping() 必须是 false。
 * typingIndicator 选择器一旦误命中常驻 DOM，isTyping() 恒为 true，
 * waitForResponse 的 `!isTyping()` 条件就**永远不成立** ⇒ 每次发送必然超时。
 * 实测抓到：Kimi 命中侧边栏骨架屏（`next-sidebar__history-loading`，224×224）、
 * ChatGLM 命中「正在加载...」占位条（`list-loading`，239×32）。
 */

/**
 * @typedef {object} SelectorAudit
 * @property {string} selector
 * @property {boolean} matched
 * @property {number} count
 * @property {Array<{tag: string, className: string, text: string, textLength?: number, childCount?: number}>} [samples]
 */

/**
 * @typedef {object} DomAudit
 * @property {SelectorAudit[]} [messageListSelectors]
 * @property {SelectorAudit[]} [typingIndicatorSelectors]
 * @property {{count?: number}} [messageList]
 * @property {boolean|null} [isTyping]
 */

/**
 * @typedef {object} ModelVerdict
 * @property {boolean} ok - 是否通过（false = 硬伤）
 * @property {number} count - 落地页上的消息计数
 * @property {string} reason - 人话解释
 * @property {string[]} falsePositiveSelectors - 命中了界面元素的选择器
 * @property {string[]} notes - 不构成硬伤、但仍需留痕的观察
 */

/**
 * 判定「消息计数模型」是否可信。
 *
 * @param {DomAudit} dom - 采集到的 DOM 审计结果
 * @returns {ModelVerdict}
 */
export function assessMessageCountModel(dom) {
  const selectors = dom?.messageListSelectors || [];
  const count = dom?.messageList?.count ?? 0;
  const matched = selectors.filter((s) => s.matched && s.count > 0);
  const typing = dom?.isTyping;

  const hardProblems = [];
  const notes = [];

  // —— 不变量 1：命中的元素必须都是空的 ——
  //
  // 「空」的判据用 **textContent 是否为空**，而不是「有没有子元素」：
  // Kimi 的 message-list-container 里有 1 个子元素，但那个子元素
  // （message-list）自己也是空的，整棵子树的 textContent 是空串。
  // 消息气泡**永远有文字**，所以 textContent 为空 ⇒ 不可能是气泡。
  const nonEmpty = matched.flatMap((s) =>
    (s.samples || [])
      .filter((x) => (x.textLength ?? 0) > 0)
      .map((x) => ({
        selector: s.selector,
        label: `${x.tag}.${String(x.className).trim().split(/\s+/)[0]}`,
        textLength: x.textLength ?? 0,
        childCount: x.childCount ?? 0,
      })),
  );

  if (nonEmpty.length > 0) {
    hardProblems.push(
      `落地页（无会话）上 messageList 命中了 ${nonEmpty.length} 个**有内容的界面元素**` +
        `（不是消息气泡）：` +
        nonEmpty
          .slice(0, 3)
          .map((x) => `${x.label}(文字 ${x.textLength} 字 / 子元素 ${x.childCount})`)
          .join("、") +
        `——计数被界面外壳撑起来，waitForResponse 的「发送前后比较」不可靠`,
    );
  } else if (count !== 0) {
    // 全是空容器：计数抬高了，但增长检测仍可用
    notes.push(
      `落地页上 messageList 命中 ${count} 个**空容器**（整棵子树没有文字）——` +
        `它们不是消息气泡，但也不影响「发送前后计数增长」的判定；` +
        `真实气泡类名仍需已登录会话确认`,
    );
  }

  // —— 不变量 2：空闲即不忙 ——
  if (typing === true) {
    const typingSamples = (dom?.typingIndicatorSelectors || [])
      .filter((s) => s.matched && s.count > 0)
      .flatMap((s) =>
        (s.samples || []).map(
          (x) => `${x.tag}.${String(x.className).trim().split(/\s+/)[0]}`,
        ),
      );
    hardProblems.push(
      `空闲落地页上 isTyping() 为 true，违反「空闲即不忙」的不变量——` +
        `typingIndicator 选择器误命中了常驻 DOM` +
        (typingSamples.length ? `（例：${typingSamples.slice(0, 3).join("、")}）` : ""),
    );
  }

  return {
    ok: hardProblems.length === 0,
    count,
    reason:
      hardProblems.length > 0
        ? hardProblems.join("；")
        : notes.length > 0
          ? notes.join("；")
          : "落地页消息数为 0、isTyping() 为 false，符合「无会话即无消息 / 空闲即不忙」的不变量",
    falsePositiveSelectors: nonEmpty.length
      ? [...new Set(nonEmpty.map((x) => x.selector))]
      : [],
    notes,
  };
}
