/**
 * Kimi Adapter
 * 月之暗面 Kimi AI 平台适配器
 */

import PlatformAdapter from './adapter.js';

class KimiAdapter extends PlatformAdapter {
  constructor() {
    super();
    this.platformId = 'kimi.com';
    this.platformName = 'Kimi AI';
    this.company = 'Moonshot AI (月之暗面)';
  }

  /**
   * 检测当前页面是否为 Kimi
   * @returns {boolean}
   */
  detectPage() {
    const hostname = window.location.hostname;
    return hostname.includes('kimi.com');
  }

  /**
   * 获取输入框选择器
   * @returns {string}
   */
  getInputSelector() {
    // Kimi 使用 textarea 作为输入框
    return 'textarea, div[contenteditable="true"]';
  }

  /**
   * 获取消息容器选择器
   * @returns {string}
   */
  getMessageSelector() {
    return '.chat-message, [class*="message"]';
  }

  /**
   * 获取发送按钮选择器
   * @returns {string}
   */
  getSendButtonSelector() {
    // 发送按钮通常在输入后有特定图标
    return 'button[type="submit"], button[aria-label*="发送"], button[class*="send"]';
  }

  /**
   * 获取输入元素
   * @returns {HTMLElement|null}
   */
  findInputElement() {
    const selector = this.getInputSelector();
    const elements = document.querySelectorAll(selector);

    // Kimi 的主输入框通常是第一个 textarea 或 contenteditable
    for (const el of elements) {
      if (el.offsetWidth > 100 && el.offsetHeight > 20) {
        return el;
      }
    }

    return elements[0] || null;
  }

  /**
   * 注入文本到输入框
   * @param {string} text
   */
  injectText(text) {
    const input = this.findInputElement();
    if (!input) {
      throw new Error('Input element not found');
    }

    input.focus();

    if (input.tagName === 'TEXTAREA') {
      // Kimi textarea 处理
      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype,
        'value'
      )?.set;

      if (nativeInputValueSetter) {
        nativeInputValueSetter.call(input, text);
      } else {
        input.value = text;
      }

      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    } else {
      // contenteditable 处理
      document.execCommand('selectAll', false, null);
      document.execCommand('delete', false, null);
      document.execCommand('insertText', false, text);
      input.dispatchEvent(new Event('input', { bubbles: true }));
    }
  }

  /**
   * 检查是否正在生成响应
   * @returns {boolean}
   */
  isTyping() {
    // Kimi 生成时通常有加载动画
    return document.querySelector('.loading, [class*="loading"], .generating') !== null;
  }

  /**
   * 获取最新响应
   * @returns {string}
   */
  getLatestResponse() {
    const messages = document.querySelectorAll(this.getMessageSelector());
    if (messages.length === 0) {
      return '';
    }

    // 获取最后一个 AI 响应
    const lastMessage = messages[messages.length - 1];
    return lastMessage.textContent?.trim() || '';
  }

  /**
   * 等待响应完成
   * @param {number} timeout
   * @returns {Promise<string>}
   */
  async waitForResponse(timeout = 60000) {
    const startTime = Date.now();
    let lastMessageCount = document.querySelectorAll(this.getMessageSelector()).length;

    return new Promise((resolve, reject) => {
      const checkInterval = setInterval(() => {
        if (Date.now() - startTime > timeout) {
          clearInterval(checkInterval);
          reject(new Error('Response timeout'));
          return;
        }

        const isTyping = this.isTyping();
        const currentMessageCount = document.querySelectorAll(this.getMessageSelector()).length;

        if (!isTyping && currentMessageCount > lastMessageCount) {
          clearInterval(checkInterval);
          resolve(this.getLatestResponse());
        }
      }, 500);
    });
  }

  /**
   * 点击发送按钮
   */
  clickSendButton() {
    const sendButton = document.querySelector(this.getSendButtonSelector());
    if (sendButton && !sendButton.disabled) {
      sendButton.click();
    } else {
      // 尝试 Enter 键发送
      const input = this.findInputElement();
      if (input) {
        input.dispatchEvent(new KeyboardEvent('keydown', {
          key: 'Enter',
          code: 'Enter',
          bubbles: true
        }));
      }
    }
  }
}

export default KimiAdapter;