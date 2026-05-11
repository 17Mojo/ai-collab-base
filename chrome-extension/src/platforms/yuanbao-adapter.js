/**
 * Yuanbao Adapter
 * 腾讯元宝 AI 平台适配器
 */

import PlatformAdapter from './adapter.js';

class YuanbaoAdapter extends PlatformAdapter {
  constructor() {
    super();
    this.platformId = 'yuanbao.tencent.com';
    this.platformName = '腾讯元宝';
    this.company = 'Tencent (腾讯)';
  }

  /**
   * 检测当前页面是否为元宝
   * @returns {boolean}
   */
  detectPage() {
    const hostname = window.location.hostname;
    return hostname.includes('yuanbao.tencent.com');
  }

  /**
   * 获取输入框选择器
   * @returns {string}
   */
  getInputSelector() {
    // 腾讯元宝通常使用 textarea 或 contenteditable
    return 'textarea, div[contenteditable="true"], [role="textbox"], input[type="text"]';
  }

  /**
   * 获取消息容器选择器
   * @returns {string}
   */
  getMessageSelector() {
    // 消息容器通常有 message、chat、response 等类名
    return '[class*="message"], [class*="chat"], [class*="response"], [class*="answer"], .message-item';
  }

  /**
   * 获取发送按钮选择器
   * @returns {string}
   */
  getSendButtonSelector() {
    return 'button[type="submit"], button[aria-label*="发送"], button[class*="send"], button[data-send]';
  }

  /**
   * 获取输入元素
   * @returns {HTMLElement|null}
   */
  findInputElement() {
    const selectors = this.getInputSelector().split(',').map(s => s.trim());

    for (const selector of selectors) {
      const elements = document.querySelectorAll(selector);
      for (const el of elements) {
        // 找到可见的、足够大的输入框
        if (el.offsetWidth > 100 && el.offsetHeight > 20) {
          return el;
        }
      }
    }

    return null;
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
      // textarea 处理 - 绕过 React 受控组件
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
    } else if (input.tagName === 'INPUT') {
      // input 处理
      input.value = text;
      input.dispatchEvent(new Event('input', { bubbles: true }));
    } else {
      // contenteditable 处理
      document.execCommand('selectAll', false, null);
      document.execCommand('delete', false, null);
      document.execCommand('insertText', false, text);
      input.dispatchEvent(new Event('input', { bubbles: true }));
    }

    // 触发 React 状态更新
    input.dispatchEvent(new Event('blur', { bubbles: true }));
    input.focus();
  }

  /**
   * 检查是否正在生成响应
   * @returns {boolean}
   */
  isTyping() {
    return document.querySelector('[class*="loading"], [class*="generating"], [class*="typing"], .spinner') !== null;
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

    // 获取最后一个 AI 消息（通常是响应）
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
      // Enter 键发送
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

export default YuanbaoAdapter;