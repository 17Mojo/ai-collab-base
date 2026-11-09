/**
 * Prompt Pack - Popup Script
 */

// DOM 元素
const packList = document.getElementById('packList');
const refreshBtn = document.getElementById('refreshBtn');
const statusEl = document.getElementById('status');
const openEditorBtn = document.getElementById('openPackEditorBtn');

/**
 * 取用户当前所在的标签页 id
 *
 * 用途：告诉后台「AI 步骤要发到哪个页面去」。
 * 不用它的话，后台只能广播 ⇒ 用户开几个 AI 页面就发几次。
 *
 * @returns {Promise<number|null>}
 */
async function getActiveTabId() {
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    return tabs?.[0]?.id ?? null;
  } catch (error) {
    // 拿不到就退回去（后台会广播），不因为这个让整个执行失败
    console.warn('Get active tab failed:', error);
    return null;
  }
}

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
      // Pack 的 id 只有一条轨道：metadata.pack_id（存储层、编辑器、执行器都用它）。
      // 此前这里写成 `pack.metadata?.pack_id || pack.pack_id || pack.id`，
      // 后两项是不存在的字段（pack.id 那次让 data-id="undefined"，点下去执行的是
      // id 为 "undefined" 的 Pack；pack.pack_id 是后端形状的顶层轨道，导入侧已收口不认）。
      //
      // N2：id/name/desc 全来自 Pack 作者（IMPORT_PACKS 只校验 pack_id 存在性），
      // innerHTML 拼接会把它们当 HTML 解析——伪造「版本过期，请输入凭据」这类
      // UI 的注入面（台账原只记输入面板，这里是同类第二处）。一律 DOM 构建：
      // 文本只走 textContent，属性只走 dataset。
      packList.textContent = '';
      for (const pack of packs) {
        const id = pack.metadata?.pack_id || '';
        // pack.name / pack.description 与上面的 pack.id 同类：从来没有任何写入方
        // 设过这两个顶层字段（写入方只有 CREATE/IMPORT，都只写 metadata.*）。
        // 留着只是把一套不存在的协议继续描述下去 ⇒ 直接去掉。
        const name = pack.metadata?.pack_name || id;
        const desc = pack.metadata?.description || '无描述';
        const li = document.createElement('li');
        li.className = 'pack-item';
        li.dataset.id = id;
        const nameEl = document.createElement('div');
        nameEl.className = 'pack-name';
        nameEl.textContent = name;
        const descEl = document.createElement('div');
        descEl.className = 'pack-desc';
        descEl.textContent = desc;
        li.append(nameEl, descEl);
        packList.appendChild(li);
      }
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
async function executePack(packId, input) {
  updateStatus('执行中...');
  clearOutputs();

  try {
    const tabId = await getActiveTabId();
    const response = await chrome.runtime.sendMessage({
      type: 'EXECUTE_PACK',
      packId,
      tabId,
      input: input || {}
    });

    if (response.success) {
      // N13：此前这里只写「执行成功」，response.result.output（7 个产出字段）
      // 直接丢弃——外部用户点了运行、报了成功、什么都没拿到。
      const count = renderOutputs(response.result?.output);
      // N8：没指定标签页时 AI 提示词是广播投递（每个内容脚本各收一次、各发一次）。
      // 不提示的话用户以为只发了一次——这里给「广播」一个真消费者。
      const broadcasted = (response.result?.steps || []).some(
        (s) => s?.delivery === 'broadcast',
      );
      const tail = broadcasted ? '（未指定标签页：提示词已广播到所有打开的 AI 页面）' : '';
      updateStatus((count ? `执行成功，${count} 个产出见下` : '执行成功（无产出字段）') + tail);
    } else {
      updateStatus(`执行失败: ${response.error}`);
    }
  } catch (error) {
    updateStatus('执行失败');
    console.error('Execute pack error:', error);
  }
}

const packInputPanel = document.getElementById('pack-input-panel');
const packInputFields = document.getElementById('pack-input-fields');
const runPackBtn = document.getElementById('run-pack-btn');
let selectedPackId = null;
let selectedRequiredFields = [];

async function selectPack(packId) {
  selectedPackId = packId;

  try {
    const result = await chrome.storage.local.get('packs');
    const packs = result.packs || [];
    const pack = packs.find(p => p.metadata?.pack_id === packId);
    const firstInputStep = pack?.workflow?.steps?.find(s => Array.isArray(s.input_fields) && s.input_fields.length);
    const fields = firstInputStep?.input_fields || [];
    // N3：必填清单来自 pack 自己声明的 config.required_fields（12 个 pack 的既有惯例）
    selectedRequiredFields = Array.isArray(firstInputStep?.config?.required_fields)
      ? firstInputStep.config.required_fields
      : [];

    // N2：字段名来自 Pack 作者（IMPORT_PACKS 不做 schema 校验），此前
    // innerHTML 拼接会把它当 HTML/属性解析——伪造输入框骗凭据的注入面。
    // 改走 DOM 构建：文本只走 textContent，属性只走 setAttribute/属性赋值，
    // 字段名永远是纯文本（含 `<` `"` 也只显示为字面量）。
    packInputFields.replaceChildren();
    for (const f of fields) {
      const required = selectedRequiredFields.includes(f);
      const label = document.createElement('label');
      label.style.cssText = 'display:block;font-size:13px;margin-bottom:6px';
      label.appendChild(document.createTextNode(f));
      if (required) {
        const star = document.createElement('span');
        star.style.color = '#c00';
        star.textContent = ' *';
        label.appendChild(star);
      }
      const input = document.createElement('input');
      input.type = 'text';
      input.setAttribute('data-field', f);
      if (required) input.setAttribute('data-required', '1');
      input.placeholder = f;
      label.appendChild(input);
      packInputFields.appendChild(label);
    }
    packInputPanel.hidden = fields.length === 0;
    updateStatus(fields.length ? `已选 ${packId}，填写输入后运行` : `已选 ${packId}`);

    if (fields.length === 0) {
      await executePack(packId, {});
    }
  } catch (error) {
    updateStatus('选择 Pack 失败');
    console.error('Select pack error:', error);
  }
}

// 事件监听
refreshBtn.addEventListener('click', loadPacks);

// 打开 Pack 编辑器（导入 Pack 的入口）
//
// 此前 popup 里**没有任何**导入入口：列表为空时只显示「请先导入 Pack」，
// 但用户既没有输入框、也没有可点的按钮能去导入 ⇒ 卡在第一步。
// 导入界面在 Pack 编辑器页里，产物是扁平布局，路径是 pack-editor.html
openEditorBtn?.addEventListener('click', async () => {
  try {
    await chrome.tabs.create({
      url: chrome.runtime.getURL('pack-editor.html')
    });
  } catch (error) {
    updateStatus('打开编辑器失败');
    console.error('Open pack editor error:', error);
  }
});

packList.addEventListener('click', (e) => {
  const item = e.target.closest('.pack-item');
  if (item && item.dataset.id) {
    selectPack(item.dataset.id);
  }
});

runPackBtn?.addEventListener('click', async () => {
  if (!selectedPackId) return;
  const input = {};
  packInputFields.querySelectorAll('input[data-field]').forEach(el => {
    input[el.dataset.field] = el.value;
  });
  // N3：必填留空不放行——空串出城会拼出「主题：。」这类残句提示词，
  // pack 还报 completed（不报错的失败，最坏的一类）。
  const missing = selectedRequiredFields.filter(f => !String(input[f] ?? '').trim());
  if (missing.length) {
    updateStatus(`请填写必填输入：${missing.join('、')}`);
    return;
  }
  await executePack(selectedPackId, input);
});

// --- 执行产出展示（N13） ---
const packOutputPanel = document.getElementById('pack-output-panel');
const packOutputFields = document.getElementById('pack-output-fields');
const exportOutputBtn = document.getElementById('export-output-btn');
let lastOutputs = null;

/**
 * 清空产出面板（新一次执行前必须清掉旧产出，否则上一轮的会冒充本轮）
 */
function clearOutputs() {
  lastOutputs = null;
  if (packOutputPanel) packOutputPanel.hidden = true;
  if (packOutputFields) packOutputFields.textContent = '';
}

/**
 * 渲染执行产出。
 *
 * 每个 output 字段一个折叠块：字段名 + 长度 + 全文 + 复制按钮；
 * 对象值按 JSON 展开。模型文本**只走 textContent**——产出是不可信内容，
 * 走 innerHTML 就是给 popup 开注入面（台账 N2 同类）。
 *
 * @param {object} outputs EXECUTE_PACK 回执的 result.output
 * @returns {number} 渲染出的字段数（0 = 没有产出可展示）
 */
function renderOutputs(outputs) {
  if (!packOutputPanel || !packOutputFields) return 0;
  const entries = Object.entries(outputs || {}).filter(([, v]) => v != null && v !== '');
  packOutputFields.textContent = '';
  for (const [key, value] of entries) {
    const text = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
    const details = document.createElement('details');
    details.className = 'output-item';
    details.dataset.field = key;

    const summary = document.createElement('summary');
    summary.textContent = `${key}（${text.length} 字）`;

    const body = document.createElement('div');
    body.className = 'output-text';
    body.dataset.testid = 'output-text';
    body.textContent = text;

    const copyBtn = document.createElement('button');
    copyBtn.className = 'btn-copy';
    copyBtn.dataset.copyField = key;
    copyBtn.textContent = '复制';

    details.append(summary, body, copyBtn);
    packOutputFields.appendChild(details);
  }
  lastOutputs = entries.length ? { ...outputs } : null;
  packOutputPanel.hidden = entries.length === 0;
  return entries.length;
}

/**
 * 产出字段的完整文本（字符串原样；对象序列化）
 * @param {string} key
 * @returns {string}
 */
function outputFieldText(key) {
  const value = lastOutputs?.[key];
  if (value == null) return '';
  return typeof value === 'string' ? value : JSON.stringify(value, null, 2);
}

/**
 * 复制单个产出字段全文
 * @param {string} key
 */
function copyOutputField(key) {
  const text = outputFieldText(key);
  if (!text) return;
  const done = () => updateStatus(`已复制 ${key}`);
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done));
  } else {
    fallbackCopy(text, done);
  }
}

/**
 * 剪贴板 API 不可用时的兜底（execCommand 已废弃，但老内核里仍管用）
 * @param {string} text
 * @param {() => void} done
 */
function fallbackCopy(text, done) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try {
    document.execCommand('copy');
    done();
  } catch (error) {
    updateStatus('复制失败，请手动选择文本');
    console.warn('Copy fallback failed:', error);
  }
  ta.remove();
}

/** 导出全部产出为 JSON 文件 */
function exportOutputs() {
  if (!lastOutputs) return;
  const json = JSON.stringify(lastOutputs, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `pack-output-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
  updateStatus('已导出 JSON');
}

packOutputFields?.addEventListener('click', (e) => {
  const btn = e.target.closest('button[data-copy-field]');
  if (!btn) return;
  copyOutputField(btn.dataset.copyField);
});

exportOutputBtn?.addEventListener('click', exportOutputs);

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
 * 往 Studio 状态区放一条纯文本状态行（N20：一律不走 innerHTML）。
 * @param {string} text
 * @param {string} [cls] - artifact-item 的附加样式类（success/error）
 */
function setStudioStatusMessage(text, cls) {
  studioStatusEl.textContent = '';
  const item = document.createElement('div');
  item.className = cls ? `artifact-item ${cls}` : 'artifact-item';
  item.textContent = text;
  studioStatusEl.appendChild(item);
}

/**
 * 显示 Studio 产物状态
 *
 * N20：artifacts 是 GENERATE_STUDIO_ARTIFACTS 的后端回执，字段
 * （content_type/mode/download_url）不许当 HTML 解析——DOM 构建 + 文本节点。
 * download_url 仅放行 ^https?:// 白名单，javascript: 等伪协议不进 href。
 * @param {object[]} artifacts
 */
function displayStudioStatus(artifacts) {
  studioStatusEl.textContent = '';
  for (const a of Array.isArray(artifacts) ? artifacts : []) {
    const item = document.createElement('div');
    item.className = `artifact-item ${a.success ? 'success' : 'error'}`;
    const icon = a.success ? '✓' : '✗';
    const mode = a.mode ? ` [${a.mode}]` : '';
    item.appendChild(document.createTextNode(`${icon} ${a.content_type}${mode}`));
    if (a.success && typeof a.download_url === 'string' && /^https?:\/\//i.test(a.download_url)) {
      item.appendChild(document.createTextNode(' '));
      const link = document.createElement('a');
      link.href = a.download_url;
      link.target = '_blank';
      link.rel = 'noopener';
      link.style.color = '#4fc3f7';
      link.textContent = '下载';
      item.appendChild(link);
    }
    studioStatusEl.appendChild(item);
  }
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
  setStudioStatusMessage('正在生成，请稍候...');

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
      setStudioStatusMessage(`生成失败: ${response?.error || '未知错误'}`, 'error');
    }
  } catch (error) {
    setStudioStatusMessage(`通信错误: ${error.message}`, 'error');
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
