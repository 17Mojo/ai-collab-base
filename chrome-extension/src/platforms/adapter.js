/**
 * Platform Adapter Interface
 * 所有平台适配器必须实现此接口
 */
import { extractMessageContent, waitForResponseGeneric } from './adapter-utils.js';
import { STABLE_MS_DEFAULT } from '../utils/wait-policy.js';

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
   * 取某条消息的正文。
   *
   * 子类可提供 `_extractContent(element)` 覆写（7 个平台有自己的抽取细节）；
   * 没有覆写时走 extractMessageContent 的「自身→后代→空串」契约
   * （不许全卡 textContent 回退，台账 N14 抽取污染）。
   *
   * @param {HTMLElement|null} element
   * @returns {string}
   */
  extractMessage(element) {
    if (typeof this._extractContent === 'function') return this._extractContent(element);
    return extractMessageContent(element, this.selectors?.messageContent || []);
  }

  /**
   * 等待 AI 响应完成（全平台统一实现，2026-11-04 收口）。
   *
   * 判定口径 = wait-policy.sampleWaitState（内容稳定才算完成），
   * 由 adapter-utils.waitForResponseGeneric 单点维护。此前 11 个平台
   * 各持一份逐字副本、各自跑旧判据（消息数增长且不在生成中）——
   * 那正是「太早成功」在 observer 路径上的残留面（台账 N14）。
   *
   * @param {number} timeout - 超时时间（毫秒）
   * @param {number} [stableMs] - 内容稳定窗口（默认生产口径 STABLE_MS_DEFAULT；测试可缩窗）
   * @returns {Promise<{messageCount: number, content: string, duration: number}>}
   */
  async waitForResponse(timeout = 60000, stableMs = STABLE_MS_DEFAULT) {
    return waitForResponseGeneric({
      getMessageList: () => this.getMessageList(),
      extractContent: (el) => this.extractMessage(el),
      isTyping: () => this.isTyping(),
      timeout,
      stableMs,
      label: this.platformId,
    });
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
