/**
 * Pack Editor Script
 * Pack CRUD 操作 + Import/Export + 可视化步骤配置
 */

// DOM 元素
const packList = document.getElementById('packList');
const packListSection = document.getElementById('packListSection');
const editorSection = document.getElementById('editorSection');
const packForm = document.getElementById('packForm');
const statusBar = document.getElementById('statusBar');

const backBtn = document.getElementById('backBtn');
const refreshBtn = document.getElementById('refreshBtn');
const newPackBtn = document.getElementById('newPackBtn');
const cancelBtn = document.getElementById('cancelBtn');
const deleteBtn = document.getElementById('deleteBtn');
const saveBtn = document.getElementById('saveBtn');

const exportAllBtn = document.getElementById('exportAllBtn');
const exportSelectedBtn = document.getElementById('exportSelectedBtn');
const importBtn = document.getElementById('importBtn');
const importFile = document.getElementById('importFile');
const importOptions = document.getElementById('importOptions');
const confirmImportBtn = document.getElementById('confirmImportBtn');

const packIdInput = document.getElementById('packId');
const packNameInput = document.getElementById('packName');
const packDescriptionInput = document.getElementById('packDescription');
const packCategorySelect = document.getElementById('packCategory');
const workflowJsonInput = document.getElementById('workflowJson');
const showJsonToggle = document.getElementById('showJsonToggle');
const stepsList = document.getElementById('stepsList');
const addStepBtn = document.getElementById('addStepBtn');

// 状态
let currentEditingPack = null;
let cachedPacks = [];
let importFileData = null;
let currentSteps = [];  // 当前编辑的步骤列表
let selectedStepIndex = -1;  // 当前选中的步骤索引

// 条件类型配置
const CONDITION_TYPES = [
  { value: 'regex_match', label: '正则匹配', needsRegex: true },
  { value: 'contains', label: '包含文本', needsValue: true },
  { value: 'equals', label: '完全相等', needsValue: true },
  { value: 'exists', label: '字段存在', needsValue: false },
  { value: 'threshold', label: '数值阈值', needsValue: true }
];

// 步骤类型配置
const STEP_TYPES = [
  { value: 'local', label: '本地处理' },
  { value: 'analysis', label: 'AI 分析' },
  { value: 'generation', label: 'AI 生成' },
  { value: 'validation', label: '交叉验证' },
  { value: 'fusion', label: '智能融合' }
];

/**
 * 更新状态栏
 */
function updateStatus(text, type = 'normal') {
  statusBar.textContent = text;
  statusBar.className = 'status-bar';
  if (type === 'success') statusBar.classList.add('success');
  if (type === 'error') statusBar.classList.add('error');
}

/**
 * 加载 Pack 列表
 */
async function loadPacks() {
  updateStatus('加载中...');

  try {
    const response = await chrome.runtime.sendMessage({ type: 'GET_ALL_PACKS' });

    if (response && response.packs) {
      cachedPacks = response.packs;
      renderPackList(cachedPacks);
      updateStatus(`已加载 ${cachedPacks.length} 个 Pack`, 'success');
    } else {
      renderEmptyState();
      updateStatus('暂无 Pack', 'error');
    }
  } catch (error) {
    console.error('Load packs error:', error);
    renderEmptyState();
    updateStatus('加载失败: ' + error.message, 'error');
  }
}

/**
 * 渲染 Pack 列表
 */
function renderPackList(packs) {
  packList.innerHTML = '';

  if (packs.length === 0) {
    renderEmptyState();
    return;
  }

  packs.forEach(pack => {
    const card = createPackCard(pack);
    packList.appendChild(card);
  });
}

/**
 * 渲染空状态
 */
function renderEmptyState() {
  packList.innerHTML = `
    <div class="empty-state">
      <p>暂无 Pack</p>
      <p>点击 "新建" 创建第一个 Pack</p>
    </div>
  `;
}

/**
 * 创建 Pack 卡片元素
 */
function createPackCard(pack) {
  const meta = pack.metadata || {};
  const packId = meta.pack_id || pack.pack_id;
  const isDefault = pack.isDefault;

  const card = document.createElement('div');
  card.className = 'pack-card';
  card.dataset.packId = packId;

  card.innerHTML = `
    <div class="pack-info">
      <h3>${meta.pack_name || meta.name || packId}</h3>
      <p>${meta.description || '无描述'}</p>
      <span class="pack-badge ${isDefault ? 'default' : 'user'}">
        ${isDefault ? '默认' : '自定义'}
      </span>
    </div>
    <div class="pack-actions">
      <button class="edit-btn">编辑</button>
      ${!isDefault ? '<button class="delete-btn">删除</button>' : ''}
    </div>
  `;

  // 编辑按钮事件
  const editBtn = card.querySelector('.edit-btn');
  editBtn.addEventListener('click', () => openEditor(pack));

  // 删除按钮事件
  const deleteBtnEl = card.querySelector('.delete-btn');
  if (deleteBtnEl) {
    deleteBtnEl.addEventListener('click', () => deletePack(packId));
  }

  return card;
}

/**
 * 打开编辑器
 */
function openEditor(pack = null) {
  editorSection.classList.add('visible');
  packListSection.style.display = 'none';

  if (pack) {
    currentEditingPack = pack;
    populateForm(pack);
    packIdInput.disabled = true; // 已有 Pack 不能修改 ID
    deleteBtn.style.display = pack.isDefault ? 'none' : 'inline-block';
    updateStatus(`编辑: ${pack.metadata?.pack_name || pack.pack_id}`);
  } else {
    currentEditingPack = null;
    clearForm();
    packIdInput.disabled = false;
    deleteBtn.style.display = 'none';
    updateStatus('新建 Pack');
  }
}

/**
 * 关闭编辑器
 */
function closeEditor() {
  editorSection.classList.remove('visible');
  packListSection.style.display = 'block';
  clearForm();
  currentEditingPack = null;
  updateStatus('就绪');
}

/**
 * 填充表单
 */
function populateForm(pack) {
  const meta = pack.metadata || {};

  packIdInput.value = meta.pack_id || pack.pack_id || '';
  packNameInput.value = meta.pack_name || meta.name || '';
  packDescriptionInput.value = meta.description || '';
  packCategorySelect.value = meta.type || 'custom';

  // Workflow - 使用可视化编辑器
  const workflow = pack.workflow || { steps: [] };
  currentSteps = workflow.steps || [];
  renderSteps();
  selectedStepIndex = -1;
}

/**
 * 清空表单
 */
function clearForm() {
  packIdInput.value = '';
  packNameInput.value = '';
  packDescriptionInput.value = '';
  packCategorySelect.value = 'custom';

  // 初始化默认步骤
  currentSteps = [
    {
      id: 'step1',
      name: 'AI 查询',
      type: 'analysis',
      branches: [],
      config: {}
    }
  ];
  renderSteps();
  selectedStepIndex = -1;
}

/**
 * 保存 Pack
 */
async function savePack(event) {
  event.preventDefault();

  // 使用新的验证功能
  const validation = validatePack();
  if (!validation.valid) {
    showValidationErrors(validation.errors);
    return;
  }

  const packId = packIdInput.value.trim();
  const packName = packNameInput.value.trim();
  const packDescription = packDescriptionInput.value.trim();
  const packCategory = packCategorySelect.value;

  // 使用可视化编辑器的步骤数据（或 JSON textarea）
  let workflow;
  if (showJsonToggle.checked) {
    try {
      workflow = JSON.parse(workflowJsonInput.value);
    } catch (e) {
      updateStatus('Workflow JSON 格式错误', 'error');
      return;
    }
  } else {
    workflow = { steps: currentSteps };
  }

  // 构建 Pack 数据
  const packData = {
    metadata: {
      pack_id: packId,
      pack_name: packName,
      version: currentEditingPack?.metadata?.version || '1.0.0',
      type: packCategory,
      description: packDescription
    },
    workflow: workflow
  };

  updateStatus('保存中...');

  try {
    const messageType = currentEditingPack ? 'UPDATE_PACK' : 'CREATE_PACK';
    const response = await chrome.runtime.sendMessage({
      type: messageType,
      packId: currentEditingPack?.metadata?.pack_id || packId,
      packData: packData
    });

    if (response.success) {
      updateStatus('保存成功!', 'success');
      closeEditor();
      await loadPacks();
    } else {
      updateStatus('保存失败: ' + response.error, 'error');
    }
  } catch (error) {
    console.error('Save pack error:', error);
    updateStatus('保存失败: ' + error.message, 'error');
  }
}

/**
 * 删除 Pack
 */
async function deletePack(packId) {
  if (!confirm(`确定要删除 Pack "${packId}" 吗？`)) {
    return;
  }

  updateStatus('删除中...');

  try {
    const response = await chrome.runtime.sendMessage({
      type: 'DELETE_PACK',
      packId: packId
    });

    if (response.success) {
      updateStatus('删除成功!', 'success');
      closeEditor();
      await loadPacks();
    } else {
      updateStatus('删除失败: ' + response.error, 'error');
    }
  } catch (error) {
    console.error('Delete pack error:', error);
    updateStatus('删除失败: ' + error.message, 'error');
  }
}

/**
 * 导出全部 Pack
 */
async function exportAllPacks() {
  updateStatus('导出中...');

  try {
    const response = await chrome.runtime.sendMessage({ type: 'EXPORT_PACKS' });

    if (response.success) {
      downloadJSON(response.data, `prompt-packs-${new Date().toISOString().split('T')[0]}.json`);
      updateStatus('导出成功!', 'success');
    } else {
      updateStatus('导出失败: ' + response.error, 'error');
    }
  } catch (error) {
    console.error('Export error:', error);
    updateStatus('导出失败: ' + error.message, 'error');
  }
}

/**
 * 导出选中 Pack
 */
async function exportSelectedPacks() {
  const selectedPacks = getSelectedPackIds();

  if (selectedPacks.length === 0) {
    updateStatus('请先选择 Pack', 'error');
    return;
  }

  updateStatus(`导出 ${selectedPacks.length} 个 Pack...`);

  try {
    const response = await chrome.runtime.sendMessage({
      type: 'EXPORT_PACKS',
      packIds: selectedPacks
    });

    if (response.success) {
      downloadJSON(response.data, `selected-packs-${new Date().toISOString().split('T')[0]}.json`);
      updateStatus('导出成功!', 'success');
    } else {
      updateStatus('导出失败: ' + response.error, 'error');
    }
  } catch (error) {
    console.error('Export error:', error);
    updateStatus('导出失败: ' + error.message, 'error');
  }
}

/**
 * 获取选中的 Pack IDs
 */
function getSelectedPackIds() {
  // 目前实现：返回所有自定义 Pack
  return cachedPacks.filter(p => !p.isDefault).map(p => p.metadata?.pack_id || p.pack_id);
}

/**
 * 下载 JSON 文件
 */
function downloadJSON(data, filename) {
  const blob = new Blob([data], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * 处理文件上传
 */
function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const content = e.target.result;
      // 验证 JSON
      const data = JSON.parse(content);
      if (!data.packs || !Array.isArray(data.packs)) {
        throw new Error('无效的 Pack 导入格式');
      }
      importFileData = content;
      importOptions.classList.add('visible');
      updateStatus(`已选择文件: ${file.name}, 包含 ${data.packs.length} 个 Pack`);
    } catch (error) {
      updateStatus('文件格式错误: ' + error.message, 'error');
      importFileData = null;
    }
  };
  reader.readAsText(file);
}

/**
 * 确认导入
 */
async function confirmImport() {
  if (!importFileData) {
    updateStatus('请先选择文件', 'error');
    return;
  }

  const mergeStrategy = document.querySelector('input[name="mergeStrategy"]:checked').value;

  updateStatus('导入中...');

  try {
    const response = await chrome.runtime.sendMessage({
      type: 'IMPORT_PACKS',
      jsonData: importFileData,
      mergeStrategy: mergeStrategy
    });

    if (response.imported && response.imported.length > 0) {
      updateStatus(`导入成功: ${response.imported.length} 个 Pack`, 'success');
      importOptions.classList.remove('visible');
      importFileData = null;
      importFile.value = '';
      await loadPacks();
    } else {
      updateStatus('导入失败: ' + (response.errors?.[0]?.error || '无 Pack 导入'), 'error');
    }
  } catch (error) {
    console.error('Import error:', error);
    updateStatus('导入失败: ' + error.message, 'error');
  }
}

// ========== 事件监听 ==========

backBtn.addEventListener('click', () => {
  // 返回设置页面或关闭
  window.close();
});

refreshBtn.addEventListener('click', async () => {
  updateStatus('刷新中...');
  await chrome.runtime.sendMessage({ type: 'REFRESH_PACKS' });
  await loadPacks();
});

newPackBtn.addEventListener('click', () => openEditor());
cancelBtn.addEventListener('click', closeEditor);
packForm.addEventListener('submit', savePack);

exportAllBtn.addEventListener('click', exportAllPacks);
exportSelectedBtn.addEventListener('click', exportSelectedPacks);
importBtn.addEventListener('click', () => importFile.click());
importFile.addEventListener('change', handleFileUpload);
confirmImportBtn.addEventListener('click', confirmImport);

// 初始化
loadPacks();

// ========== 可视化步骤编辑 ==========

/**
 * 渲染步骤列表
 */
function renderSteps() {
  stepsList.innerHTML = '';

  if (currentSteps.length === 0) {
    stepsList.innerHTML = `
      <div class="empty-state" style="padding: 20px; text-align: center; color: #888;">
        <p>暂无步骤</p>
        <p style="font-size: 12px;">点击 "+ 添加步骤" 开始配置</p>
      </div>
    `;
    return;
  }

  currentSteps.forEach((step, index) => {
    const stepCard = createStepCard(step, index);
    stepsList.appendChild(stepCard);
  });

  // 同步到 JSON textarea
  syncStepsToJson();
}

/**
 * 创建步骤卡片
 */
function createStepCard(step, index) {
  const card = document.createElement('div');
  card.className = `step-item ${selectedStepIndex === index ? 'selected' : ''}`;
  card.dataset.stepIndex = index;

  const stepTypeLabel = STEP_TYPES.find(t => t.value === step.type)?.label || step.type;

  card.innerHTML = `
    <div class="step-header">
      <span class="step-name">${step.name || step.id}</span>
      <span class="step-type-badge">${stepTypeLabel}</span>
    </div>
    <div class="step-fields">
      <input type="text" class="field-input step-id-input" placeholder="步骤 ID" value="${step.id}" data-step="${index}" data-field="id">
      <input type="text" class="field-input step-name-input" placeholder="步骤名称" value="${step.name || ''}" data-step="${index}" data-field="name">
      <select class="field-input step-type-select" data-step="${index}" data-field="type">
        ${STEP_TYPES.map(t => `<option value="${t.value}" ${step.type === t.value ? 'selected' : ''}>${t.label}</option>`).join('')}
      </select>
      <input type="text" class="field-input step-output-input" placeholder="输出字段" value="${step.output_field || ''}" data-step="${index}" data-field="output_field">
    </div>
    <div class="branch-config">
      <div class="branch-header">
        <span class="branch-title">🔀 分支条件 (${step.branches?.length || 0})</span>
        <button class="add-branch-btn" data-add-branch="${index}">+ 添加分支</button>
      </div>
      <div id="branches-${index}">
        ${(step.branches || []).map((b, bi) => createBranchItem(index, bi, b)).join('')}
      </div>
    </div>
    <div style="margin-top: 10px; display: flex; gap: 8px;">
      <select class="field-input step-next-step-select" style="width: 150px;" data-step="${index}" data-field="next_step">
        <option value="">顺序执行</option>
        <option value="end" ${step.next_step === 'end' ? 'selected' : ''}>结束流程</option>
        ${currentSteps.map(s => `<option value="${s.id}" ${step.next_step === s.id ? 'selected' : ''}>跳转: ${s.name || s.id}</option>`).join('')}
      </select>
      <select class="field-input step-on-error-select" style="width: 150px;" data-step="${index}" data-field="on_error">
        <option value="">无错误处理</option>
        ${currentSteps.map(s => `<option value="${s.id}" ${step.on_error === s.id ? 'selected' : ''}>错误: ${s.name || s.id}</option>`).join('')}
      </select>
      <button class="branch-btn delete-step-btn" data-delete-step="${index}">删除步骤</button>
    </div>
  `;

  return card;
}

/**
 * 创建分支条件 UI
 */
function createBranchItem(stepIndex, branchIndex, branch) {
  const conditionTypeLabel = CONDITION_TYPES.find(c => c.value === branch.condition_type)?.label || branch.condition_type;
  const needsRegex = branch.condition_type === 'regex_match';
  const needsValue = ['contains', 'equals', 'threshold'].includes(branch.condition_type);

  return `
    <div class="branch-item" id="branch-${stepIndex}-${branchIndex}" data-step="${stepIndex}" data-branch="${branchIndex}">
      <div class="branch-row">
        <select class="branch-select condition-type-select" data-step="${stepIndex}" data-branch="${branchIndex}" data-field="condition_type">
          ${CONDITION_TYPES.map(c => `<option value="${c.value}" ${branch.condition_type === c.value ? 'selected' : ''}>${c.label}</option>`).join('')}
        </select>
        <select class="branch-select target-step-select" data-step="${stepIndex}" data-branch="${branchIndex}" data-field="target_step">
          ${currentSteps.map(s => `<option value="${s.id}" ${branch.target_step === s.id ? 'selected' : ''}>→ ${s.name || s.id}</option>`).join('')}
        </select>
        <button class="branch-btn delete-branch-btn" data-step="${stepIndex}" data-branch="${branchIndex}">删除</button>
      </div>
      ${needsValue ? `
        <div class="branch-row">
          <input type="text" class="branch-input condition-value-input" placeholder="匹配值" value="${branch.condition_value || ''}" data-step="${stepIndex}" data-branch="${branchIndex}" data-field="condition_value">
          <label style="font-size: 12px; color: #888; display: flex; align-items: center; gap: 4px;">
            <input type="checkbox" class="negate-checkbox" ${branch.negate ? 'checked' : ''} data-step="${stepIndex}" data-branch="${branchIndex}" data-field="negate">
            否定
          </label>
        </div>
      ` : ''}
      ${needsRegex ? `
        <div class="regex-config">
          <div class="regex-row">
            <input type="text" class="branch-input regex-pattern" placeholder="正则模式 (如: ^SUCCESS:|完成)"
              value="${branch.regex_config?.pattern || ''}"
              data-step="${stepIndex}" data-branch="${branchIndex}" data-regex="pattern">
            <input type="text" class="branch-input regex-flags" placeholder="标志" value="${branch.regex_config?.flags || 'i'}"
              data-step="${stepIndex}" data-branch="${branchIndex}" data-regex="flags">
            <button class="regex-test-btn" data-step="${stepIndex}" data-branch="${branchIndex}">测试</button>
          </div>
          <div class="regex-test-result" id="regex-result-${stepIndex}-${branchIndex}">
            <input type="text" class="regex-test-input" placeholder="输入测试文本..." data-step="${stepIndex}" data-branch="${branchIndex}">
            <div class="regex-test-output"></div>
          </div>
          <label style="font-size: 12px; color: #888; display: flex; align-items: center; gap: 4px; margin-top: 4px;">
            <input type="checkbox" class="negate-checkbox" ${branch.negate ? 'checked' : ''} data-step="${stepIndex}" data-branch="${branchIndex}" data-field="negate">
            否定 (匹配相反情况)
          </label>
        </div>
      ` : ''}
    </div>
  `;
}

/**
 * 添加步骤
 */
function addStep() {
  const newStep = {
    id: `step_${currentSteps.length + 1}`,
    name: `步骤 ${currentSteps.length + 1}`,
    type: 'analysis',
    branches: [],
    config: {}
  };

  currentSteps.push(newStep);
  renderSteps();
  updateStatus(`添加步骤: ${newStep.id}`, 'success');
}

/**
 * 删除步骤
 */
function deleteStep(index) {
  if (!confirm('确定删除此步骤？')) return;

  currentSteps.splice(index, 1);
  if (selectedStepIndex === index) selectedStepIndex = -1;
  renderSteps();
  updateStatus('步骤已删除', 'success');
}

/**
 * 更新步骤字段
 */
function updateStepField(index, field, value) {
  if (currentSteps[index]) {
    currentSteps[index][field] = value;
    syncStepsToJson();
  }
}

/**
 * 添加分支
 */
function addBranch(stepIndex) {
  if (!currentSteps[stepIndex].branches) {
    currentSteps[stepIndex].branches = [];
  }

  currentSteps[stepIndex].branches.push({
    condition_type: 'regex_match',
    target_step: currentSteps[0]?.id || '',
    regex_config: {
      pattern: '',
      flags: 'i'
    },
    negate: false
  });

  renderSteps();
}

/**
 * 删除分支
 */
function deleteBranch(stepIndex, branchIndex) {
  if (currentSteps[stepIndex]?.branches) {
    currentSteps[stepIndex].branches.splice(branchIndex, 1);
    renderSteps();
  }
}

/**
 * 更新分支字段
 */
function updateBranchField(stepIndex, branchIndex, field, value) {
  const branch = currentSteps[stepIndex]?.branches?.[branchIndex];
  if (branch) {
    branch[field] = value;
    // 如果切换到 regex_match，初始化 regex_config
    if (field === 'condition_type' && value === 'regex_match' && !branch.regex_config) {
      branch.regex_config = { pattern: '', flags: 'i' };
    }
    renderSteps();
  }
}

/**
 * 更新分支正则配置
 */
function updateBranchRegex(stepIndex, branchIndex, field, value) {
  const branch = currentSteps[stepIndex]?.branches?.[branchIndex];
  if (branch && branch.regex_config) {
    branch.regex_config[field] = value;
    syncStepsToJson();
  }
}

/**
 * 同步步骤数据到 JSON textarea
 */
function syncStepsToJson() {
  const workflow = { steps: currentSteps };
  workflowJsonInput.value = JSON.stringify(workflow, null, 2);
}

/**
 * 从 JSON 解析步骤数据
 */
function parseStepsFromJson() {
  try {
    const workflow = JSON.parse(workflowJsonInput.value);
    currentSteps = workflow.steps || [];
    renderSteps();
  } catch (e) {
    console.error('Parse JSON error:', e);
  }
}

// ========== 正则表达式测试功能 ==========

/**
 * 测试正则表达式
 * @param {number} stepIndex
 * @param {number} branchIndex
 * @param {string} testText
 */
function testRegex(stepIndex, branchIndex, testText) {
  const branch = currentSteps[stepIndex]?.branches?.[branchIndex];
  if (!branch?.regex_config?.pattern) {
    return { matched: false, error: '请先输入正则模式' };
  }

  try {
    const pattern = branch.regex_config.pattern;
    const flags = branch.regex_config.flags || 'i';
    const regex = new RegExp(pattern, flags);
    const match = testText.match(regex);

    return {
      matched: match !== null,
      matchText: match?.[0] || null,
      groups: match?.groups || {},
      index: match?.index
    };
  } catch (e) {
    return { matched: false, error: `正则错误: ${e.message}` };
  }
}

/**
 * 显示正则测试结果
 * @param {number} stepIndex
 * @param {number} branchIndex
 */
function showRegexTestResult(stepIndex, branchIndex) {
  const resultDiv = document.getElementById(`regex-result-${stepIndex}-${branchIndex}`);
  const testInput = resultDiv?.querySelector('.regex-test-input');
  const outputDiv = resultDiv?.querySelector('.regex-test-output');

  if (!testInput || !outputDiv) return;

  const testText = testInput.value || '';
  const result = testRegex(stepIndex, branchIndex, testText);

  resultDiv.classList.add('visible');

  if (result.error) {
    resultDiv.className = 'regex-test-result visible nomatch';
    outputDiv.textContent = result.error;
  } else if (result.matched) {
    resultDiv.className = 'regex-test-result visible match';
    outputDiv.innerHTML = `
      ✅ 匹配成功<br>
      匹配内容: "${result.matchText}"<br>
      ${Object.keys(result.groups).length > 0 ? `提取字段: ${JSON.stringify(result.groups)}` : ''}
    `;
  } else {
    resultDiv.className = 'regex-test-result visible nomatch';
    outputDiv.textContent = '❌ 未匹配';
  }
}

// ========== 验证功能 ==========

/**
 * 验证 Pack 数据
 * @returns {Object} { valid: boolean, errors: string[] }
 */
function validatePack() {
  const errors = [];

  // 验证 Pack ID
  const packId = packIdInput.value.trim();
  if (!packId) {
    errors.push('Pack ID 不能为空');
    packIdInput.classList.add('error');
  } else if (!/^[a-z0-9-]+$/.test(packId)) {
    errors.push('Pack ID 只能包含小写字母、数字和连字符');
    packIdInput.classList.add('error');
  } else {
    packIdInput.classList.remove('error');
  }

  // 验证 Pack 名称
  const packName = packNameInput.value.trim();
  if (!packName) {
    errors.push('Pack 名称不能为空');
    packNameInput.classList.add('error');
  } else {
    packNameInput.classList.remove('error');
  }

  // 验证步骤
  if (currentSteps.length === 0) {
    errors.push('至少需要添加一个步骤');
  }

  currentSteps.forEach((step, index) => {
    if (!step.id) {
      errors.push(`步骤 ${index + 1} ID 不能为空`);
    }

    // 验证分支
    (step.branches || []).forEach((branch, bi) => {
      if (!branch.target_step) {
        errors.push(`步骤 ${step.id} 的分支 ${bi + 1} 需要指定目标步骤`);
      }

      if (branch.condition_type === 'regex_match' && !branch.regex_config?.pattern) {
        errors.push(`步骤 ${step.id} 的正则分支 ${bi + 1} 需要输入正则模式`);
      }
    });
  });

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * 显示验证错误
 * @param {string[]} errors
 */
function showValidationErrors(errors) {
  if (errors.length === 0) return;

  const errorMessages = errors.map(e => `• ${e}`).join('\n');
  updateStatus(`验证失败:\n${errorMessages}`, 'error');
}

// ========== 事件委托（修复超时问题） ==========

/**
 * 设置事件委托
 */
function setupEventDelegation() {
  // 步骤字段事件委托
  stepsList.addEventListener('change', (e) => {
    const target = e.target;

    // 步骤字段更新
    if (target.dataset.step && target.dataset.field) {
      const stepIndex = parseInt(target.dataset.step);
      const field = target.dataset.field;
      updateStepField(stepIndex, field, target.value);
    }

    // 正则字段更新
    if (target.dataset.step && target.dataset.branch && target.dataset.regex) {
      const stepIndex = parseInt(target.dataset.step);
      const branchIndex = parseInt(target.dataset.branch);
      const regexField = target.dataset.regex;
      updateBranchRegex(stepIndex, branchIndex, regexField, target.value);
    }

    // 分支字段更新
    if (target.dataset.step && target.dataset.branch && target.dataset.field && !target.dataset.regex) {
      const stepIndex = parseInt(target.dataset.step);
      const branchIndex = parseInt(target.dataset.branch);
      const field = target.dataset.field;

      if (field === 'negate') {
        updateBranchField(stepIndex, branchIndex, field, target.checked);
      } else {
        updateBranchField(stepIndex, branchIndex, field, target.value);
      }
    }
  });

  // 按钮点击事件委托
  stepsList.addEventListener('click', (e) => {
    const target = e.target;

    // 添加分支
    if (target.dataset.addBranch) {
      const stepIndex = parseInt(target.dataset.addBranch);
      addBranch(stepIndex);
    }

    // 删除步骤
    if (target.dataset.deleteStep) {
      const stepIndex = parseInt(target.dataset.deleteStep);
      deleteStep(stepIndex);
    }

    // 删除分支
    if (target.classList.contains('delete-branch-btn')) {
      const stepIndex = parseInt(target.dataset.step);
      const branchIndex = parseInt(target.dataset.branch);
      deleteBranch(stepIndex, branchIndex);
    }

    // 正则测试按钮
    if (target.classList.contains('regex-test-btn')) {
      const stepIndex = parseInt(target.dataset.step);
      const branchIndex = parseInt(target.dataset.branch);

      // 显示测试区域
      const resultDiv = document.getElementById(`regex-result-${stepIndex}-${branchIndex}`);
      if (resultDiv) {
        resultDiv.classList.add('visible');
      }
    }
  });

  // 正则测试输入事件
  stepsList.addEventListener('input', (e) => {
    const target = e.target;

    // 正则测试输入
    if (target.classList.contains('regex-test-input')) {
      const stepIndex = parseInt(target.dataset.step);
      const branchIndex = parseInt(target.dataset.branch);
      showRegexTestResult(stepIndex, branchIndex);
    }
  });
}

// JSON 显示切换
showJsonToggle.addEventListener('change', (e) => {
  workflowJsonInput.style.display = e.target.checked ? 'block' : 'none';
  if (e.target.checked) {
    syncStepsToJson();
  }
});

// JSON textarea 编辑同步
workflowJsonInput.addEventListener('change', () => {
  parseStepsFromJson();
});

// 添加步骤按钮
addStepBtn.addEventListener('click', addStep);

// 初始化事件委托
setupEventDelegation();

// 全局函数导出（保持兼容）
globalThis.updateStepField = updateStepField;
globalThis.updateBranchField = updateBranchField;
globalThis.updateBranchRegex = updateBranchRegex;
globalThis.addBranch = addBranch;
globalThis.deleteBranch = deleteBranch;
globalThis.deleteStep = deleteStep;