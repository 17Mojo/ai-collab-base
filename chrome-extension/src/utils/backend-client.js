/**
 * Prompt Pack - Backend Client
 * HTTP client for Local Backend API (http://127.0.0.1:8000)
 */

const BACKEND_BASE_URL = 'http://127.0.0.1:8000';
const DEFAULT_TIMEOUT = 30000; // 30 seconds

/**
 * Backend Client Class
 * Handles all HTTP communication with Local Backend
 */
class BackendClient {
  constructor(baseUrl = BACKEND_BASE_URL) {
    this.baseUrl = baseUrl;
    this.timeout = DEFAULT_TIMEOUT;
    this._connected = false;
  }

  /**
   * Make HTTP request to Local Backend
   * @param {string} endpoint - API endpoint (e.g., '/api/consensus/generate')
   * @param {Object} options - Request options
   * @returns {Promise<Object>}
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const {
      method = 'GET',
      body = null,
      headers = {},
      timeout = this.timeout
    } = options;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...headers
        },
        body: body ? JSON.stringify(body) : null,
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
      }

      this._connected = true;
      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      this._connected = false;
      if (error.name === 'AbortError') {
        throw new Error('Request timeout');
      }
      throw error;
    }
  }

  /**
   * Generate consensus from multiple AI providers
   * @param {string} topic - Topic to generate consensus on
   * @param {Object} options - Additional options
   * @param {Array} options.real_responses - Chrome收集的真实响应（混合模式）
   * @returns {Promise<Object>}
   */
  async generateConsensus(topic, options = {}) {
    return this.request('/api/consensus/generate', {
      method: 'POST',
      body: {
        topic,
        providers: options.providers,
        timeout: options.timeout,
        // 混合模式：发送真实响应给Backend
        real_responses: options.real_responses
      },
      timeout: options.timeout || 60000 // Longer timeout for consensus
    });
  }

  /**
   * Inject soul/personality into content
   * @param {string} consensus - Consensus content
   * @param {string} profileName - Soul profile name
   * @param {Object} options - Additional options
   * @returns {Promise<Object>}
   */
  async injectSoul(consensus, profileName = 'luoyonghao', options = {}) {
    return this.request('/api/soul/inject', {
      method: 'POST',
      body: {
        consensus,
        profile_name: profileName,
        timeout: options.timeout
      }
    });
  }

  /**
   * Generate styled prompt with soul profile
   * @param {string} originalPrompt - Original user prompt
   * @param {string} profileName - Soul profile name
   * @returns {Promise<Object>}
   */
  async stylePrompt(originalPrompt, profileName = 'luoyonghao') {
    return this.request('/api/soul/style_prompt', {
      method: 'POST',
      body: {
        original_prompt: originalPrompt,
        profile_name: profileName
      }
    });
  }

  /**
   * Check backend health
   * @returns {Promise<Object>}
   */
  async checkHealth() {
    return this.request('/health');
  }

  /**
   * List available consensus providers
   * @returns {Promise<Object>}
   */
  async listProviders() {
    return this.request('/api/consensus/providers');
  }

  /**
   * List available soul profiles
   * @returns {Promise<Object>}
   */
  async listProfiles() {
    return this.request('/api/soul/profiles');
  }

  /**
   * Get pack metadata
   * @param {string} packId - Pack ID
   * @returns {Promise<Object>}
   */
  async getPackMetadata(packId) {
    return this.request(`/api/packs/${packId}/metadata`);
  }

  // ========== Pack API Methods ==========

  /**
   * List packs from backend
   * @param {Object} options - Pagination/filtering options
   * @returns {Promise<Object>}
   */
  async listPacks(options = {}) {
    const { skip = 0, limit = 50, category = null, search = null } = options;
    let endpoint = `/api/packs/?skip=${skip}&limit=${limit}`;
    if (category) endpoint += `&category=${category}`;
    if (search) endpoint += `&search=${encodeURIComponent(search)}`;
    return this.request(endpoint);
  }

  /**
   * Get single pack from backend
   * @param {string} packId
   * @returns {Promise<Object>}
   */
  async getPack(packId) {
    return this.request(`/api/packs/${packId}`);
  }

  /**
   * Create pack on backend
   * @param {Object} packData
   * @returns {Promise<Object>}
   */
  async createPack(packData) {
    return this.request('/api/packs/', {
      method: 'POST',
      body: packData
    });
  }

  /**
   * Update pack on backend
   * @param {string} packId
   * @param {Object} packData
   * @returns {Promise<Object>}
   */
  async updatePack(packId, packData) {
    return this.request(`/api/packs/${packId}`, {
      method: 'PUT',
      body: packData
    });
  }

  /**
   * Delete pack on backend
   * @param {string} packId
   * @returns {Promise<void>}
   */
  async deletePack(packId) {
    return this.request(`/api/packs/${packId}`, {
      method: 'DELETE'
    });
  }

  /**
   * Bulk create packs
   * @param {Array} packs
   * @returns {Promise<Object>}
   */
  async bulkCreatePacks(packs) {
    return this.request('/api/packs/bulk/create', {
      method: 'POST',
      body: { packs, continue_on_error: true }
    });
  }

  // ========== Style API Methods ==========

  /**
   * List all styles (preset + custom)
   * @returns {Promise<Object>}
   */
  async listStyles() {
    return this.request('/api/soul/styles');
  }

  /**
   * Get single style
   * @param {string} name - Style name
   * @returns {Promise<Object>}
   */
  async getStyle(name) {
    return this.request(`/api/soul/styles/${name}`);
  }

  /**
   * Create custom style
   * @param {Object} styleData
   * @returns {Promise<Object>}
   */
  async createStyle(styleData) {
    return this.request('/api/soul/styles', {
      method: 'POST',
      body: styleData
    });
  }

  /**
   * Update custom style
   * @param {string} name - Style name
   * @param {Object} styleData
   * @returns {Promise<Object>}
   */
  async updateStyle(name, styleData) {
    return this.request(`/api/soul/styles/${name}`, {
      method: 'PUT',
      body: styleData
    });
  }

  /**
   * Delete custom style
   * @param {string} name - Style name
   * @returns {Promise<Object>}
   */
  async deleteStyle(name) {
    return this.request(`/api/soul/styles/${name}`, {
      method: 'DELETE'
    });
  }

  // ========== Workflow Methods ==========

  /**
   * Get full workflow: consensus + soul injection
   * @param {string} topic - Topic/question
   * @param {string} soulProfile - Soul profile name
   * @param {Object} options - Additional options
   * @returns {Promise<Object>}
   */
  async executeFullWorkflow(topic, soulProfile = 'luoyonghao', options = {}) {
    console.log('[Backend Client] Starting full workflow for:', topic);

    // Step 1: Generate consensus
    console.log('[Backend Client] Generating consensus...');
    const consensusResult = await this.generateConsensus(topic, options);

    // Step 2: Inject soul
    console.log('[Backend Client] Injecting soul profile:', soulProfile);
    const soulResult = await this.injectSoul(
      consensusResult.consensus,
      soulProfile,
      options
    );

    // Return combined result
    return {
      topic,
      consensus: consensusResult,
      soulInjection: soulResult,
      finalContent: soulResult.personalized_content,
      mode: consensusResult.mode,
      timestamp: new Date().toISOString()
    };
  }

  /**
   * Check if backend is connected
   * @returns {boolean}
   */
  isConnected() {
    return this._connected;
  }
}

// Export as global module (following settings-handler pattern)
globalThis.backendClient = new BackendClient();

// Also export for ES module usage
export default BackendClient;