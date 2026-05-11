/**
 * Prompt Pack - Popup Script
 */

// DOM 元素
const packList = document.getElementById('packList');
const refreshBtn = document.getElementById('refreshBtn');
const statusEl = document.getElementById('status');

/**
 * 更新状态显示
 * @param {string} text
 */
function updateStatus(text) {
  statusEl.textContent = `状态: ${text}`;
}

/**
 * 加载 Pack 列表
 */
async function loadPacks() {
  updateStatus('加载中...');

  try {
    // 从 storage 获取 Pack 列表
    const result = await chrome.storage.local.get('packs');
    const packs = result.packs || [];

    if (packs.length === 0) {
      packList.innerHTML = `
        <li class="pack-item">
          <div class="pack-name">暂无 Pack</div>
          <div class="pack-desc">请先导入 Pack</div>
        </li>
      `;
    } else {
      packList.innerHTML = packs.map(pack => `
        <li class="pack-item" data-id="${pack.id}">
          <div class="pack-name">${pack.name}</div>
          <div class="pack-desc">${pack.description || '无描述'}</div>
        </li>
      `).join('');
    }

    updateStatus('就绪');
  } catch (error) {
    updateStatus('加载失败');
    console.error('Load packs error:', error);
  }
}

/**
 * 执行 Pack
 * @param {string} packId
 */
async function executePack(packId) {
  updateStatus('执行中...');

  try {
    const response = await chrome.runtime.sendMessage({
      type: 'EXECUTE_PACK',
      packId
    });

    if (response.success) {
      updateStatus('执行成功');
    } else {
      updateStatus(`执行失败: ${response.error}`);
    }
  } catch (error) {
    updateStatus('执行失败');
    console.error('Execute pack error:', error);
  }
}

// 事件监听
refreshBtn.addEventListener('click', loadPacks);

packList.addEventListener('click', (e) => {
  const item = e.target.closest('.pack-item');
  if (item && item.dataset.id) {
    executePack(item.dataset.id);
  }
});

// --- Studio 产物生成 ---
const studioAudioCb = document.getElementById('studio-audio');
const studioVideoCb = document.getElementById('studio-video');
const studioSlidesCb = document.getElementById('studio-slides');
const generateStudioBtn = document.getElementById('generate-studio-btn');
const studioStatusEl = document.getElementById('studio-status');

let currentNotebookId = null;

/**
 * 获取选中的 Studio 产物类型
 * @returns {string[]}
 */
function getSelectedStudioTypes() {
  const types = [];
  if (studioAudioCb.checked) types.push('audio');
  if (studioVideoCb.checked) types.push('video');
  if (studioSlidesCb.checked) types.push('slides');
  return types;
}

/**
 * 更新生成按钮状态
 */
function updateGenerateBtnState() {
  generateStudioBtn.disabled = getSelectedStudioTypes().length === 0;
}

/**
 * 显示 Studio 产物状态
 * @param {object[]} artifacts
 */
function displayStudioStatus(artifacts) {
  studioStatusEl.innerHTML = artifacts.map(a => {
    const cls = a.success ? 'success' : 'error';
    const icon = a.success ? '✓' : '✗';
    const mode = a.mode ? ` [${a.mode}]` : '';
    const detail = a.success && a.download_url
      ? ` <a href="${a.download_url}" target="_blank" style="color:#4fc3f7">下载</a>`
      : '';
    return `<div class="artifact-item ${cls}">${icon} ${a.content_type}${mode}${detail}</div>`;
  }).join('');
}

/**
 * 生成 Studio 产物
 */
async function generateStudioArtifacts() {
  const selectedTypes = getSelectedStudioTypes();
  if (selectedTypes.length === 0) return;

  const focusText = document.getElementById('studio-focus-text').value;
  generateStudioBtn.disabled = true;
  generateStudioBtn.textContent = '生成中...';
  studioStatusEl.innerHTML = '<div class="artifact-item">正在生成，请稍候...</div>';

  try {
    const response = await chrome.runtime.sendMessage({
      type: 'GENERATE_STUDIO_ARTIFACTS',
      notebookId: currentNotebookId,
      contentTypes: selectedTypes,
      focus: focusText
    });

    if (response && response.success) {
      displayStudioStatus(response.artifacts);
    } else {
      studioStatusEl.innerHTML = `<div class="artifact-item error">生成失败: ${response?.error || '未知错误'}</div>`;
    }
  } catch (error) {
    studioStatusEl.innerHTML = `<div class="artifact-item error">通信错误: ${error.message}</div>`;
  } finally {
    generateStudioBtn.disabled = false;
    generateStudioBtn.textContent = '生成 Studio 产物';
    updateGenerateBtnState();
  }
}

// Studio checkbox 事件
[studioAudioCb, studioVideoCb, studioSlidesCb].forEach(cb => {
  cb.addEventListener('change', updateGenerateBtnState);
});

generateStudioBtn.addEventListener('click', generateStudioArtifacts);

// 初始化
loadPacks();
