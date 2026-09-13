/**
 * Adapter Utilities
 * 平台适配器的共享工具函数，消除重复代码
 */

/**
 * 查找元素（支持多个选择器回退）
 * @param {string[]} selectors - 选择器数组，按优先级排列
 * @returns {HTMLElement|null}
 */
export function findElement(selectors) {
  for (const selector of selectors) {
    const el = document.querySelector(selector);
    if (el) return el;
  }
  return null;
}

/**
 * 查找所有匹配元素（支持多个选择器回退）
 * @param {string[]} selectors - 选择器数组，按优先级排列
 * @returns {NodeList}
 */
export function findElements(selectors) {
  for (const selector of selectors) {
    const els = document.querySelectorAll(selector);
    if (els.length > 0) return els;
  }
  return document.querySelectorAll('div'); // fallback: empty NodeList
}

/**
 * 注入文本到 textarea 元素（绕过 React 受控组件）
 * @param {HTMLElement} input - textarea 输入框
 * @param {string} text - 要注入的文本
 */
export function injectIntoTextarea(input, text) {
  const nativeSetter = Object.getOwnPropertyDescriptor(
    window.HTMLTextAreaElement.prototype,
    'value'
  )?.set;

  if (nativeSetter) {
    nativeSetter.call(input, text);
  } else {
    input.value = text;
  }

  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
}

/**
 * 注入文本到 Lexical 编辑器（通过 __lexicalEditor API）
 * Lexical 是 Meta 的富文本编辑器框架，React 状态管理会覆盖 DOM 修改，
 * 必须通过 Lexical 的 parseEditorState + setEditorState API 注入。
 * @param {HTMLElement} input - Lexical 编辑器根元素
 * @param {string} text - 要注入的文本
 * @returns {boolean} 是否成功注入
 */
export function injectIntoLexical(input, text) {
  const editor = input.__lexicalEditor;
  if (!editor || !editor.parseEditorState || !editor.setEditorState) {
    return false;
  }

  try {
    const newStateJSON = {
      root: {
        children: [{
          children: [{
            detail: 0,
            format: 0,
            mode: 'normal',
            style: '',
            text: text,
            type: 'text',
            version: 1,
          }],
          direction: 'ltr',
          format: '',
          indent: 0,
          type: 'paragraph',
          version: 1,
          textFormat: 0,
        }],
        direction: 'ltr',
        format: '',
        indent: 0,
        type: 'root',
        version: 1,
      },
    };

    const newState = editor.parseEditorState(JSON.stringify(newStateJSON));
    editor.setEditorState(newState);
    return true;
  } catch (e) {
    return false;
  }
}

/**
 * 注入文本到 contenteditable div
 * @param {HTMLElement} input - contenteditable 输入框
 * @param {string} text - 要注入的文本
 */
export function injectIntoContentEditable(input, text) {
  input.focus();

  // 优先检测 Lexical 编辑器
  if (input.__lexicalEditor) {
    if (injectIntoLexical(input, text)) return;
  }

  document.execCommand('selectAll', false, null);
  document.execCommand('delete', false, null);
  document.execCommand('insertText', false, text);

  // 如果 execCommand 未生效（React 等框架可能拦截），使用 innerHTML 回退
  if (!input.textContent.includes(text)) {
    const paragraph = input.querySelector('p');
    if (paragraph) {
      paragraph.textContent = text;
    } else {
      input.innerHTML = '<p>' + text + '</p>';
    }
  }

  input.dispatchEvent(new Event('input', { bubbles: true }));
}

/**
 * 注入文本到 role="textbox" 元素
 * @param {HTMLElement} input - textbox 输入框
 * @param {string} text - 要注入的文本
 */
export function injectIntoTextbox(input, text) {
  input.focus();

  // 优先检测 Lexical 编辑器
  if (input.__lexicalEditor) {
    if (injectIntoLexical(input, text)) return;
  }

  // 尝试 execCommand
  document.execCommand('selectAll', false, null);
  document.execCommand('delete', false, null);
  document.execCommand('insertText', false, text);

  // 如果 execCommand 未生效，回退到直接设置
  if (!input.textContent.includes(text)) {
    const paragraph = input.querySelector('p');
    if (paragraph) {
      paragraph.textContent = text;
    } else {
      input.innerHTML = '<p>' + text + '</p>';
    }
  }

  input.dispatchEvent(new Event('input', { bubbles: true }));
}

/**
 * 注入文本到 input[type="text"] 元素
 * @param {HTMLElement} input - input 输入框
 * @param {string} text - 要注入的文本
 */
export function injectIntoInput(input, text) {
  input.value = text;
  input.dispatchEvent(new Event('input', { bubbles: true }));
}

/**
 * 智能注入文本到输入框（自动识别元素类型）
 * @param {HTMLElement} input - 输入框元素
 * @param {string} text - 要注入的文本
 */
export function injectTextSmart(input, text) {
  input.focus();

  if (input.tagName === 'TEXTAREA') {
    injectIntoTextarea(input, text);
  } else if (input.tagName === 'INPUT') {
    injectIntoInput(input, text);
  } else if (input.getAttribute('role') === 'textbox') {
    injectIntoTextbox(input, text);
  } else if (input.isContentEditable) {
    injectIntoContentEditable(input, text);
  } else {
    // fallback: 尝试 insertText
    document.execCommand('insertText', false, text);
  }

  // 触发 React 状态更新（blur + focus）
  input.dispatchEvent(new Event('blur', { bubbles: true }));
  input.focus();
}

/**
 * 查找可见的输入框元素
 * @param {string[]} selectors - 选择器数组
 * @returns {HTMLElement|null}
 */
export function findVisibleInput(selectors) {
  for (const selector of selectors) {
    const elements = document.querySelectorAll(selector);
    for (const el of elements) {
      if (el.offsetWidth > 100 && el.offsetHeight > 20) {
        return el;
      }
    }
  }
  // fallback: 返回第一个匹配元素
  for (const selector of selectors) {
    const el = document.querySelector(selector);
    if (el) return el;
  }
  return null;
}

/**
 * 等待 AI 响应完成（通用实现）
 * @param {Function} getMessageListFn - 获取消息列表的函数
 * @param {Function} isTypingFn - 检查是否正在输入的函数
 * @param {number} timeout - 超时时间（毫秒）
 * @returns {Promise<Object>}
 */
export async function waitForResponseGeneric(getMessageListFn, isTypingFn, timeout = 60000) {
  const startTime = Date.now();
  const initialMessageCount = getMessageListFn().length;

  return new Promise((resolve, reject) => {
    const checkInterval = setInterval(() => {
      if (Date.now() - startTime > timeout) {
        clearInterval(checkInterval);
        reject(new Error('Response timeout'));
        return;
      }

      const currentMessageCount = getMessageListFn().length;
      const isStillTyping = isTypingFn();

      if (currentMessageCount > initialMessageCount && !isStillTyping) {
        clearInterval(checkInterval);
        const latestMessage = getMessageListFn()[getMessageListFn().length - 1];
        resolve({
          messageCount: currentMessageCount,
          duration: Date.now() - startTime,
        });
      }
    }, 500);
  });
}

/**
 * 点击发送按钮（通用实现）
 * @param {HTMLElement|null} sendButton - 发送按钮元素
 * @param {Function} findInputElementFn - 查找输入框的函数
 */
export async function clickSendGeneric(sendButton, findInputElementFn) {
  if (sendButton && !sendButton.disabled) {
    sendButton.click();
    await new Promise((resolve) => setTimeout(resolve, 100));
    return;
  }

  // fallback: Enter 键发送
  const input = findInputElementFn();
  if (input) {
    input.dispatchEvent(new KeyboardEvent('keydown', {
      key: 'Enter',
      code: 'Enter',
      bubbles: true,
    }));
  }
}

/**
 * 提取消息内容（通用实现）
 * @param {HTMLElement} messageElement - 消息元素
 * @param {string[]} contentSelectors - 内容选择器数组
 * @returns {string}
 */
export function extractMessageContent(messageElement, contentSelectors = []) {
  if (!messageElement) return '';

  for (const selector of contentSelectors) {
    const contentEl = messageElement.querySelector(selector);
    if (contentEl) return contentEl.textContent.trim();
  }

  // fallback: 直接取 textContent
  return messageElement.textContent?.trim() || '';
}

/**
 * 延迟工具函数
 */
export function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}