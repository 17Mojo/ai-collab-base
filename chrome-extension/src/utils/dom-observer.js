/**
 * DOM Observer
 * 监控 DOM 变化，检测 AI 响应状态
 */

/**
 * DOM Observer 类
 */
class DOMObserver {
  /**
   * @param {Object} options - 配置选项
   */
  constructor(options = {}) {
    this.observers = new Map();
    this.callbacks = new Map();
    this.options = {
      subtree: true,
      childList: true,
      attributes: true,
      characterData: true,
      ...options
    };
  }

  /**
   * 开始观察元素
   * @param {HTMLElement|string} target - 目标元素或选择器
   * @param {string} id - 观察器标识
   * @param {Function} callback - 变化回调
   * @returns {MutationObserver}
   */
  observe(target, id, callback) {
    // 获取目标元素
    const element = typeof target === 'string'
      ? document.querySelector(target)
      : target;

    if (!element) {
      console.warn(`[DOMObserver] Target not found: ${target}`);
      return null;
    }

    // 如果已存在同名观察器，先停止
    this.stop(id);

    // 创建观察器
    const observer = new MutationObserver((mutations) => {
      const changes = this._processMutations(mutations);
      callback(changes, element);
    });

    // 开始观察
    observer.observe(element, this.options);

    // 保存引用
    this.observers.set(id, observer);
    this.callbacks.set(id, callback);

    return observer;
  }

  /**
   * 停止观察
   * @param {string} id - 观察器标识
   */
  stop(id) {
    const observer = this.observers.get(id);
    if (observer) {
      observer.disconnect();
      this.observers.delete(id);
      this.callbacks.delete(id);
    }
  }

  /**
   * 停止所有观察
   */
  stopAll() {
    for (const id of this.observers.keys()) {
      this.stop(id);
    }
  }

  /**
   * 处理变化记录
   * @param {MutationRecord[]} mutations
   * @returns {Object}
   */
  _processMutations(mutations) {
    const changes = {
      addedNodes: [],
      removedNodes: [],
      attributeChanges: [],
      textChanges: []
    };

    for (const mutation of mutations) {
      switch (mutation.type) {
        case 'childList':
          // 添加的节点
          for (const node of mutation.addedNodes) {
            if (node.nodeType === Node.ELEMENT_NODE) {
              changes.addedNodes.push(node);
            }
          }
          // 移除的节点
          for (const node of mutation.removedNodes) {
            if (node.nodeType === Node.ELEMENT_NODE) {
              changes.removedNodes.push(node);
            }
          }
          break;

        case 'attributes':
          changes.attributeChanges.push({
            target: mutation.target,
            attributeName: mutation.attributeName,
            oldValue: mutation.oldValue,
            newValue: mutation.target.getAttribute(mutation.attributeName)
          });
          break;

        case 'characterData':
          changes.textChanges.push({
            target: mutation.target,
            oldValue: mutation.oldValue,
            newValue: mutation.target.textContent
          });
          break;
      }
    }

    return changes;
  }

  /**
   * 观察消息列表变化
   * @param {string} selector - 消息列表选择器
   * @param {Function} onMessageAdded - 新消息回调
   * @returns {MutationObserver}
   */
  observeMessages(selector, onMessageAdded) {
    return this.observe(selector, 'messages', (changes) => {
      for (const node of changes.addedNodes) {
        onMessageAdded(node);
      }
    });
  }

  /**
   * 观察输入状态变化
   * @param {string} selector - 输入框选择器
   * @param {Function} onInputChange - 输入变化回调
   * @returns {MutationObserver}
   */
  observeInput(selector, onInputChange) {
    return this.observe(selector, 'input', (changes, element) => {
      const textContent = element.textContent || element.innerText;
      onInputChange(textContent, changes);
    });
  }

  /**
   * 观察 AI 输入状态
   * @param {string} typingSelector - 输入指示器选择器
   * @param {Function} onTypingChange - 状态变化回调
   * @returns {MutationObserver}
   */
  observeTypingStatus(typingSelector, onTypingChange) {
    let wasTyping = false;

    const checkTyping = () => {
      const isTyping = document.querySelector(typingSelector) !== null;
      if (isTyping !== wasTyping) {
        wasTyping = isTyping;
        onTypingChange(isTyping);
      }
    };

    // 使用 body 作为观察目标
    return this.observe(document.body, 'typing', () => {
      checkTyping();
    });
  }

  /**
   * 获取观察器状态
   * @returns {Object}
   */
  getStatus() {
    return {
      activeObservers: this.observers.size,
      observerIds: Array.from(this.observers.keys())
    };
  }
}

export default DOMObserver;
