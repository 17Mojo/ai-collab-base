/**
 * ChatGLM Adapter
 * 智谱清言 AI 平台适配器
 */

import PlatformAdapter from './adapter.js';

class ChatGLMAdapter extends PlatformAdapter {
  constructor() {
    super();
    this.platformId = 'chatglm.cn';
    this.platformName = '智谱清言';
    this.company = 'Zhipu AI (智谱AI)';
  }

  /**
   * 检测当前页面是否为 ChatGLM
   * @returns {boolean}
   */
  detectPage() {
    const hostname = window.location.hostname;
    return hostname.includes('chatglm.cn');
  }

  /**
   * 获取输入框选择器
   * @returns {string}
   */
  getInputSelector() {
    // ChatGLM 使用 textbox
    return 'textbox, textarea, div[contenteditable="true"]';
  }

  /**
   * 获取消息容器选择器
   * @returns {string}
   */
  getMessageSelector() {
    return '.chat-message, [class*="message"], [class*="response"]';
  }

  /**
   * 获取发送按钮选择器
   * @returns {string}
   */
  getSendButtonSelector() {
    // ChatGLM 发送按钮
    return 'button[type="submit"], button[aria-label*="发送"], button[class*="send"]';
  }

  /**
   * 获取输入元素
   * @returns {HTMLElement|null}
   */
  findInputElement() {
    const textboxes = document.querySelectorAll('[role="textbox"]');
    const textareas = document.querySelectorAll('textarea');
    const contentEditables = document.querySelectorAll('div[contenteditable="true"]');

    // 找到可见的输入框
    for (const el of [...textboxes, ...textareas, ...contentEditables]) {
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

    if (input.tagName === 'TEXTAREA' || input.getAttribute('role') === 'textbox') {
      // textbox 处理
      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype,
        'value'
      )?.set;

      if (nativeInputValueSetter && input.tagName === 'TEXTAREA') {
        nativeInputValueSetter.call(input, text);
      } else {
        // 对于 role="textbox" 的元素
        input.textContent = text;
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

    // ChatGLM 需要额外触发 React 事件
    input.dispatchEvent(new Event('blur', { bubbles: true }));
    input.focus();
  }

  /**
   * 检查是否正在生成响应
   * @returns {boolean}
   */
  isTyping() {
    // ChatGLM 生成时的状态
    return document.querySelector('[class*="loading"], [class*="generating"], .typing-indicator') !== null;
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

export default ChatGLMAdapter;