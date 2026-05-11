/**
 * Pack Storage Manager
 * Pack 缓存管理器 - 同步 Backend API + chrome.storage + DEFAULT_PACKS
 */

/**
 * Pack Storage Manager Class
 * 管理 Pack 的缓存、同步、CRUD 操作
 */
class PackStorageManager {
  /**
   * @param {Object} backendClient - BackendClient instance
   */
  constructor(backendClient) {
    this.backendClient = backendClient;
    this.cacheKey = 'packCache';
    this.cacheTimestampKey = 'packCacheTimestamp';
    this.cacheTTL = 5 * 60 * 1000; // 5 minutes
    this._initialized = false;
  }

  /**
   * Initialize - 从缓存加载，合并 DEFAULT_PACKS
   * @returns {Promise<void>}
   */
  async initialize() {
    console.log('[PackStorage] Initializing...');

    try {
      // 尝试从 chrome.storage.local 加载缓存
      const result = await chrome.storage.local.get([this.cacheKey, this.cacheTimestampKey]);
      const cachedPacks = result[this.cacheKey];
      const cacheTimestamp = result[this.cacheTimestampKey];

      // 检查缓存是否过期
      if (cachedPacks && !this._isCacheExpired(cacheTimestamp)) {
        console.log('[PackStorage] Using cached packs:', cachedPacks.packs?.length || 0);
        this._initialized = true;
        return;
      }

      // 缓存过期或不存在，从 Backend 同步
      console.log('[PackStorage] Cache expired or empty, syncing from backend...');
      await this.refreshCache(false);

      this._initialized = true;
    } catch (error) {
      console.warn('[PackStorage] Initialize failed, using defaults:', error);
      this._initialized = true;
    }
  }

  /**
   * 检查缓存是否过期
   * @param {number} timestamp
   * @returns {boolean}
   */
  _isCacheExpired(timestamp) {
    if (!timestamp) return true;
    return Date.now() - timestamp > this.cacheTTL;
  }

  /**
   * 获取所有 Pack (缓存 + DEFAULT_PACKS 合并)
   * @returns {Promise<Array>}
   */
  async getAllPacks() {
    // 确保 initialized
    if (!this._initialized) {
      await this.initialize();
    }

    try {
      const result = await chrome.storage.local.get(this.cacheKey);
      const cachedPacks = result[this.cacheKey]?.packs || [];

      // 合并 DEFAULT_PACKS
      const allPacks = this.mergeWithDefaults(cachedPacks);

      console.log('[PackStorage] getAllPacks:', allPacks.length, 'packs');
      return allPacks;
    } catch (error) {
      console.error('[PackStorage] getAllPacks error:', error);
      // Fallback: 只返回 DEFAULT_PACKS
      return this._getDefaultPacksArray();
    }
  }

  /**
   * 获取单个 Pack
   * @param {string} packId
   * @returns {Promise<Object|null>}
   */
  async getPack(packId) {
    const packs = await this.getAllPacks();
    return packs.find(p => p.metadata?.pack_id === packId) || null;
  }

  /**
   * 从 Backend API 刷新缓存
   * @param {boolean} force - 强制刷新（忽略 TTL）
   * @returns {Promise<void>}
   */
  async refreshCache(force = false) {
    console.log('[PackStorage] Refreshing cache, force:', force);

    try {
      // 从 Backend 获取 Packs
      const response = await this.backendClient.listPacks({ limit: 100 });
      const userPacks = response.packs || [];

      // 保存到 chrome.storage.local
      const cacheData = {
        packs: userPacks,
        lastSync: new Date().toISOString(),
        version: '2.0.0'
      };

      await chrome.storage.local.set({
        [this.cacheKey]: cacheData,
        [this.cacheTimestampKey]: Date.now()
      });

      console.log('[PackStorage] Cache refreshed:', userPacks.length, 'packs from backend');
    } catch (error) {
      console.warn('[PackStorage] Refresh cache failed:', error);
      // Backend 连接失败，保持现有缓存
    }
  }

  /**
   * 创建 Pack
   * @param {Object} packData
   * @returns {Promise<Object>}
   */
  async createPack(packData) {
    console.log('[PackStorage] Creating pack:', packData.metadata?.pack_id);

    try {
      // 调用 Backend API 创建
      const newPack = await this.backendClient.createPack(packData);

      // 更新缓存
      await this._addToCache(newPack);

      console.log('[PackStorage] Pack created:', newPack.pack_id);
      return this._transformPackFromBackend(newPack);
    } catch (error) {
      console.error('[PackStorage] Create pack failed:', error);
      throw error;
    }
  }

  /**
   * 更新 Pack
   * @param {string} packId
   * @param {Object} packData
   * @returns {Promise<Object>}
   */
  async updatePack(packId, packData) {
    console.log('[PackStorage] Updating pack:', packId);

    try {
      // 调用 Backend API 更新
      const updatedPack = await this.backendClient.updatePack(packId, packData);

      // 更新缓存
      await this._updateInCache(packId, updatedPack);

      console.log('[PackStorage] Pack updated:', packId);
      return this._transformPackFromBackend(updatedPack);
    } catch (error) {
      console.error('[PackStorage] Update pack failed:', error);
      throw error;
    }
  }

  /**
   * 删除 Pack
   * @param {string} packId
   * @returns {Promise<void>}
   */
  async deletePack(packId) {
    console.log('[PackStorage] Deleting pack:', packId);

    // 检查是否是 DEFAULT_PACKS
    if (this._isDefaultPack(packId)) {
      throw new Error('Cannot delete default pack');
    }

    try {
      // 调用 Backend API 删除
      await this.backendClient.deletePack(packId);

      // 从缓存移除
      await this._removeFromCache(packId);

      console.log('[PackStorage] Pack deleted:', packId);
    } catch (error) {
      console.error('[PackStorage] Delete pack failed:', error);
      throw error;
    }
  }

  /**
   * 导入 Packs
   * @param {string} jsonData - JSON 字符串
   * @param {string} mergeStrategy - 'merge' | 'overwrite'
   * @returns {Promise<Object>}
   */
  async importPacks(jsonData, mergeStrategy = 'merge') {
    console.log('[PackStorage] Importing packs, strategy:', mergeStrategy);

    try {
      const data = JSON.parse(jsonData);
      const packsToImport = data.packs || [];

      if (!packsToImport.length) {
        throw new Error('No packs found in import data');
      }

      const imported = [];
      const errors = [];

      // 批量创建到 Backend
      for (const pack of packsToImport) {
        try {
          // 转换格式为 Backend 期望的结构
          const backendPack = this._transformPackForBackend(pack);
          const newPack = await this.backendClient.createPack(backendPack);
          imported.push(this._transformPackFromBackend(newPack));
        } catch (err) {
          errors.push({ pack_id: pack.metadata?.pack_id, error: err.message });
        }
      }

      // 刷新缓存
      await this.refreshCache(true);

      console.log('[PackStorage] Import complete:', imported.length, 'success,', errors.length, 'errors');
      return { imported, errors, total: packsToImport.length };
    } catch (error) {
      console.error('[PackStorage] Import failed:', error);
      throw error;
    }
  }

  /**
   * 导出 Packs
   * @param {Array<string>|null} packIds - 要导出的 Pack IDs（null = 全部）
   * @returns {Promise<string>}
   */
  async exportPacks(packIds = null) {
    console.log('[PackStorage] Exporting packs:', packIds || 'all');

    const packs = await this.getAllPacks();

    // 过滤指定的 Pack
    const packsToExport = packIds
      ? packs.filter(p => packIds.includes(p.metadata?.pack_id))
      : packs;

    // 构建导出格式
    const exportData = {
      version: '2.0.0',
      exportedAt: new Date().toISOString(),
      source: 'prompt-pack-extension',
      packs: packsToExport.map(p => this._sanitizePackForExport(p))
    };

    return JSON.stringify(exportData, null, 2);
  }

  /**
   * 合并 DEFAULT_PACKS 与用户 Packs
   * @param {Array} userPacks
   * @returns {Array}
   */
  mergeWithDefaults(userPacks) {
    const defaultPacksArray = this._getDefaultPacksArray();

    // 用户 Pack 覆盖同 ID 的默认 Pack（允许自定义）
    const merged = [...defaultPacksArray];

    for (const userPack of userPacks) {
      const packId = userPack.metadata?.pack_id || userPack.pack_id;
      const existingIndex = merged.findIndex(p => p.metadata?.pack_id === packId);

      if (existingIndex >= 0) {
        // 用户 Pack 覆盖默认 Pack
        merged[existingIndex] = {
          ...merged[existingIndex],
          ...this._transformPackFromBackend(userPack),
          isDefault: false,
          isUserPack: true
        };
      } else {
        // 新增用户 Pack
        merged.push({
          ...this._transformPackFromBackend(userPack),
          isDefault: false,
          isUserPack: true
        });
      }
    }

    return merged;
  }

  /**
   * 获取 DEFAULT_PACKS 数组格式
   * @returns {Array}
   */
  _getDefaultPacksArray() {
    // 从 service-worker.js 的 DEFAULT_PACKS 获取
    // 这里硬编码以避免模块依赖问题
    const DEFAULT_PACKS = {
      'knowledge-query': {
        metadata: {
          pack_id: 'knowledge-query',
          pack_name: '知识问答',
          description: '多平台并发查询 → 共识提取 → 灵魂注入',
          version: '2.0',
          type: 'productivity'
        },
        workflow: {
          steps: [
            {
              id: 'query',
              name: '多平台查询',
              type: 'ai',
              prompt_template: '{{prompt}}',
              config: {
                multiPlatform: true,
                soulProfile: '{{soulProfile}}'
              }
            }
          ]
        }
      },
      'article-writing': {
        metadata: {
          pack_id: 'article-writing',
          pack_name: '文章写作',
          description: '收集观点 → 共识整合 → 个性化输出',
          version: '2.0',
          type: 'creative'
        },
        workflow: {
          steps: [
            {
              id: 'collect',
              name: '观点收集',
              type: 'ai',
              prompt_template: '关于{{topic}}的观点和见解',
              config: {
                multiPlatform: true,
                soulProfile: '{{soulProfile}}'
              }
            }
          ]
        }
      }
    };

    return Object.entries(DEFAULT_PACKS).map(([id, pack]) => ({
      ...pack,
      isDefault: true,
      isUserPack: false
    }));
  }

  /**
   * 检查是否是 DEFAULT_PACKS
   * @param {string} packId
   * @returns {boolean}
   */
  _isDefaultPack(packId) {
    return ['knowledge-query', 'article-writing'].includes(packId);
  }

  /**
   * 添加 Pack 到缓存
   * @param {Object} pack
   */
  async _addToCache(pack) {
    const result = await chrome.storage.local.get(this.cacheKey);
    const cacheData = result[this.cacheKey] || { packs: [], version: '2.0.0' };

    cacheData.packs.push(pack);

    await chrome.storage.local.set({
      [this.cacheKey]: cacheData,
      [this.cacheTimestampKey]: Date.now()
    });
  }

  /**
   * 更新缓存中的 Pack
   * @param {string} packId
   * @param {Object} pack
   */
  async _updateInCache(packId, pack) {
    const result = await chrome.storage.local.get(this.cacheKey);
    const cacheData = result[this.cacheKey] || { packs: [], version: '2.0.0' };

    const index = cacheData.packs.findIndex(p => p.pack_id === packId);
    if (index >= 0) {
      cacheData.packs[index] = pack;
    }

    await chrome.storage.local.set({
      [this.cacheKey]: cacheData,
      [this.cacheTimestampKey]: Date.now()
    });
  }

  /**
   * 从缓存移除 Pack
   * @param {string} packId
   */
  async _removeFromCache(packId) {
    const result = await chrome.storage.local.get(this.cacheKey);
    const cacheData = result[this.cacheKey] || { packs: [], version: '2.0.0' };

    cacheData.packs = cacheData.packs.filter(p => p.pack_id !== packId);

    await chrome.storage.local.set({
      [this.cacheKey]: cacheData,
      [this.cacheTimestampKey]: Date.now()
    });
  }

  /**
   * 转换 Backend 格式为内部格式
   * @param {Object} backendPack
   * @returns {Object}
   */
  _transformPackFromBackend(backendPack) {
    // Backend 返回的格式: { pack_id, pack_name, version, pack_data }
    // 内部格式: { metadata, workflow }
    if (backendPack.metadata && backendPack.workflow) {
      return backendPack; // 已经是正确格式
    }

    return {
      metadata: {
        pack_id: backendPack.pack_id,
        pack_name: backendPack.pack_name,
        version: backendPack.version,
        type: backendPack.type || 'custom',
        description: backendPack.description || ''
      },
      workflow: backendPack.pack_data?.workflow || { steps: [] },
      ...backendPack
    };
  }

  /**
   * 转换内部格式为 Backend 格式
   * @param {Object} pack
   * @returns {Object}
   */
  _transformPackForBackend(pack) {
    return {
      metadata: pack.metadata,
      workflow: pack.workflow,
      quality_metrics: pack.quality_metrics || null,
      generation_params: pack.generation_params || null,
      system_prompt: pack.system_prompt || ''
    };
  }

  /**
   * 清理 Pack 数据用于导出
   * @param {Object} pack
   * @returns {Object}
   */
  _sanitizePackForExport(pack) {
    return {
      metadata: {
        pack_id: pack.metadata?.pack_id,
        pack_name: pack.metadata?.pack_name,
        version: pack.metadata?.version,
        type: pack.metadata?.type || 'custom',
        description: pack.metadata?.description || ''
      },
      workflow: pack.workflow || { steps: [] },
      isDefault: pack.isDefault || false
    };
  }

  /**
   * 获取存储状态
   * @returns {Promise<Object>}
   */
  async getStorageInfo() {
    const result = await chrome.storage.local.get([this.cacheKey, this.cacheTimestampKey]);
    return {
      initialized: this._initialized,
      cacheExists: !!result[this.cacheKey],
      cacheTimestamp: result[this.cacheTimestampKey],
      cacheExpired: this._isCacheExpired(result[this.cacheTimestampKey]),
      packCount: result[this.cacheKey]?.packs?.length || 0
    };
  }
}

// Export as global module (following backend-client pattern)
globalThis.packStorageManager = null; // Will be initialized in service-worker

// Also export for ES module usage
export default PackStorageManager;