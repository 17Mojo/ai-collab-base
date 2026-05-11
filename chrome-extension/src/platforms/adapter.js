/**
 * Platform Adapter Interface
 * 所有平台适配器必须实现此接口
 */
class PlatformAdapter {
  /**
   * @param {string} platformId - 平台标识符
   */
  constructor(platformId) {
    this.platformId = platformId;
  }

  /**
   * 检测当前页面是否匹配此平台
   * @returns {boolean}
   */
  detect() {
    throw new Error('detect() must be implemented');
  }

  /**
   * 获取聊天输入框
   * @returns {HTMLElement|null}
   */
  getChatInput() {
    throw new Error('getChatInput() must be implemented');
  }

  /**
   * 获取发送按钮
   * @returns {HTMLElement|null}
   */
  getSendButton() {
    throw new Error('getSendButton() must be implemented');
  }

  /**
   * 获取消息列表
   * @returns {NodeList}
   */
  getMessageList() {
    throw new Error('getMessageList() must be implemented');
  }

  /**
   * 获取最新消息
   * @returns {HTMLElement|null}
   */
  getLatestMessage() {
    const messages = this.getMessageList();
    return messages.length > 0 ? messages[messages.length - 1] : null;
  }

  /**
   * 注入文本到输入框
   * @param {string} text
   * @returns {Promise<void>}
   */
  async injectText(text) {
    throw new Error('injectText() must be implemented');
  }

  /**
   * 点击发送按钮
   * @returns {Promise<void>}
   */
  async clickSend() {
    throw new Error('clickSend() must be implemented');
  }

  /**
   * 等待 AI 响应完成
   * @param {number} timeout - 超时时间（毫秒）
   * @returns {Promise<Object>}
   */
  async waitForResponse(timeout = 60000) {
    throw new Error('waitForResponse() must be implemented');
  }

  /**
   * 检查 AI 是否正在输入
   * @returns {boolean}
   */
  isTyping() {
    throw new Error('isTyping() must be implemented');
  }

  /**
   * 获取平台配置
   * @returns {Object}
   */
  getConfig() {
    return {
      platformId: this.platformId,
      selectors: {},
      timeouts: {
        response: 60000,
        typing: 5000
      }
    };
  }
}

export default PlatformAdapter;
