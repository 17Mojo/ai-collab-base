/**
 * 风格编辑器逻辑
 * 支持：风格列表展示、创建、编辑、删除、预览
 */

const API_BASE = 'http://127.0.0.1:8000';

// DOM 元素
const stylesGrid = document.getElementById('stylesGrid');
const editorPanel = document.getElementById('editorPanel');
const previewPanel = document.getElementById('previewPanel');
const editorTitle = document.getElementById('editorTitle');
const styleBadge = document.getElementById('styleBadge');
const styleForm = document.getElementById('styleForm');
const createBtn = document.getElementById('createBtn');
const backBtn = document.getElementById('backBtn');
const saveBtn = document.getElementById('saveBtn');
const cancelBtn = document.getElementById('cancelBtn');
const deleteBtn = document.getElementById('deleteBtn');
const toast = document.getElementById('toast');

// 表单字段
const styleName = document.getElementById('styleName');
const displayName = document.getElementById('displayName');
const stylePrefix = document.getElementById('stylePrefix');
const styleSuffix = document.getElementById('styleSuffix');
const styleTone = document.getElementById('styleTone');
const styleKeywords = document.getElementById('styleKeywords');

// 预览字段
const previewOriginal = document.getElementById('previewOriginal');
const previewStyled = document.getElementById('previewStyled');

// 状态
let currentEditingStyle = null;
let allStyles = [];

/**
 * 加载所有风格
 */
async function loadStyles() {
  try {
    const response = await fetch(`${API_BASE}/api/soul/styles`);
    const data = await response.json();

    allStyles = data.styles || [];
    renderStyleGrid(allStyles);
  } catch (error) {
    console.error('Failed to load styles:', error);
    showToast('加载风格失败', true);
    stylesGrid.innerHTML = '<div class="empty-state">无法连接后端服务</div>';
  }
}

/**
 * 渲染风格卡片网格
 */
function renderStyleGrid(styles) {
  stylesGrid.innerHTML = '';

  if (styles.length === 0) {
    stylesGrid.innerHTML = '<div class="empty-state">暂无风格</div>';
    return;
  }

  styles.forEach(style => {
    const card = document.createElement('div');
    card.className = `style-card ${style.is_preset ? 'preset' : ''}`;
    card.dataset.name = style.name;

    const badgeHtml = style.is_preset
      ? '<span class="style-badge">预设</span>'
      : '<span class="style-badge custom">自定义</span>';

    const previewText = style.prefix + '示例提问' + style.suffix;

    card.innerHTML = `
      ${badgeHtml}
      <div class="style-name">${style.display_name}</div>
      <div class="style-tone">${style.tone || '无基调描述'}</div>
      <div class="style-preview">${previewText.slice(0, 50)}${previewText.length > 50 ? '...' : ''}</div>
    `;

    card.addEventListener('click', () => openEditor(style));
    stylesGrid.appendChild(card);
  });
}

/**
 * 打开编辑器
 */
function openEditor(style = null) {
  currentEditingStyle = style;

  // 设置编辑器标题
  if (style) {
    editorTitle.textContent = style.is_preset ? '查看风格' : '编辑风格';
    styleBadge.innerHTML = style.is_preset
      ? '<span class="style-badge">预设</span>'
      : '<span class="style-badge custom">自定义</span>';

    // 填充表单
    styleName.value = style.name;
    displayName.value = style.display_name;
    stylePrefix.value = style.prefix;
    styleSuffix.value = style.suffix;
    styleTone.value = style.tone;
    styleKeywords.value = style.keywords.join(', ');

    // 预设风格不可编辑
    if (style.is_preset) {
      styleName.disabled = true;
      displayName.disabled = true;
      stylePrefix.disabled = true;
      styleSuffix.disabled = true;
      styleTone.disabled = true;
      styleKeywords.disabled = true;
      saveBtn.disabled = true;
      deleteBtn.style.display = 'none';
    } else {
      enableForm();
      deleteBtn.style.display = 'inline-block';
    }

    // 更新预览
    updatePreview();
  } else {
    // 新建风格
    editorTitle.textContent = '创建新风格';
    styleBadge.innerHTML = '';

    clearForm();
    enableForm();
    deleteBtn.style.display = 'none';
  }

  editorPanel.classList.add('active');
  previewPanel.classList.add('active');
}

/**
 * 启用表单字段
 */
function enableForm() {
  styleName.disabled = false;
  displayName.disabled = false;
  stylePrefix.disabled = false;
  styleSuffix.disabled = false;
  styleTone.disabled = false;
  styleKeywords.disabled = false;
  saveBtn.disabled = false;
}

/**
 * 清空表单
 */
function clearForm() {
  styleName.value = '';
  displayName.value = '';
  stylePrefix.value = '';
  styleSuffix.value = '';
  styleTone.value = '';
  styleKeywords.value = '';
  previewStyled.textContent = '';
}

/**
 * 关闭编辑器
 */
function closeEditor() {
  editorPanel.classList.remove('active');
  previewPanel.classList.remove('active');
  currentEditingStyle = null;
  clearForm();
}

/**
 * 更新预览
 */
function updatePreview() {
  const original = previewOriginal.textContent;
  const prefix = stylePrefix.value;
  const suffix = styleSuffix.value;

  previewStyled.textContent = prefix + original + suffix;
}

/**
 * 表单输入监听（实时预览）
 */
stylePrefix.addEventListener('input', updatePreview);
styleSuffix.addEventListener('input', updatePreview);

/**
 * 保存风格
 */
async function saveStyle(e) {
  e.preventDefault();

  const styleData = {
    name: styleName.value.trim(),
    display_name: displayName.value.trim() || styleName.value.trim(),
    prefix: stylePrefix.value,
    suffix: styleSuffix.value,
    tone: styleTone.value.trim(),
    keywords: styleKeywords.value.split(',').map(k => k.trim()).filter(k => k)
  };

  if (!styleData.name) {
    showToast('风格名称必填', true);
    return;
  }

  try {
    let response;
    if (currentEditingStyle && !currentEditingStyle.is_preset) {
      // 更新已有风格
      response = await fetch(`${API_BASE}/api/soul/styles/${currentEditingStyle.name}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(styleData)
      });
    } else {
      // 创建新风格
      response = await fetch(`${API_BASE}/api/soul/styles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(styleData)
      });
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '保存失败');
    }

    showToast('风格已保存');
    closeEditor();
    await loadStyles();
  } catch (error) {
    console.error('Save style error:', error);
    showToast(error.message, true);
  }
}

/**
 * 删除风格
 */
async function deleteStyle() {
  if (!currentEditingStyle || currentEditingStyle.is_preset) {
    return;
  }

  if (!confirm(`确定删除风格 "${currentEditingStyle.display_name}"？`)) {
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/api/soul/styles/${currentEditingStyle.name}`, {
      method: 'DELETE'
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '删除失败');
    }

    showToast('风格已删除');
    closeEditor();
    await loadStyles();
  } catch (error) {
    console.error('Delete style error:', error);
    showToast(error.message, true);
  }
}

/**
 * 显示 Toast 提示
 */
function showToast(message, isError = false) {
  toast.textContent = message;
  toast.className = `toast ${isError ? 'error' : ''} show`;

  setTimeout(() => {
    toast.classList.remove('show');
  }, 2000);
}

/**
 * 事件绑定
 */
createBtn.addEventListener('click', () => openEditor(null));
cancelBtn.addEventListener('click', closeEditor);
backBtn.addEventListener('click', () => {
  window.close();
});
deleteBtn.addEventListener('click', deleteStyle);
styleForm.addEventListener('submit', saveStyle);

/**
 * 初始化
 */
loadStyles();