/**
 * LongCat Adapter
 * LongCat AI 平台适配器
 */

import PlatformAdapter from './adapter.js';

class LongCatAdapter extends PlatformAdapter {
  constructor() {
    super();
    this.platformId = 'longcat.chat';
    this.platformName = 'LongCat AI';
    this.company = 'LongCat';
  }

  /**
   * 检测当前页面是否为 LongCat
   * @returns {boolean}
   */
  detectPage() {
    const hostname = window.location.hostname;
    return hostname.includes('longcat.chat');
  }

  /**
   * 获取输入框选择器
   * @returns {string}
   */
  getInputSelector() {
    return 'textbox, div[role="textbox"], div[contenteditable="true"]';
  }

  /**
   * 获取消息容器选择器
   * @returns {string}
   */
  getMessageSelector() {
    return '.message, [class*="response"], [class*="chat-item"]';
  }

  /**
   * 获取发送按钮选择器
   * @returns {string}
   */
  getSendButtonSelector() {
    return 'button[type="submit"], img[cursor=pointer]';
  }

  /**
   * 获取输入元素
   * @returns {HTMLElement|null}
   */
  findInputElement() {
    const textboxes = document.querySelectorAll('[role="textbox"]');
    const contentEditables = document.querySelectorAll('div[contenteditable="true"]');

    for (const el of [...textboxes, ...contentEditables]) {
      if (el.offsetWidth > 100 && el.offsetHeight > 20) {
        return el;
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

    // textbox 处理
    if (input.getAttribute('role') === 'textbox') {
      const paragraph = input.querySelector('p');
      if (paragraph) {
        paragraph.textContent = text;
      } else {
        input.textContent = text;
      }
      input.dispatchEvent(new Event('input', { bubbles: true }));
    } else {
      // contenteditable 处理
      document.execCommand('selectAll', false, null);
      document.execCommand('delete', false, null);
      document.execCommand('insertText', false, text);
      input.dispatchEvent(new Event('input', { bubbles: true }));
    }

    input.dispatchEvent(new Event('blur', { bubbles: true }));
    input.focus();
  }

  /**
   * 检查是否正在生成响应
   * @returns {boolean}
   */
  isTyping() {
    return document.querySelector('[class*="loading"], [class*="generating"]') !== null;
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

export default LongCatAdapter;