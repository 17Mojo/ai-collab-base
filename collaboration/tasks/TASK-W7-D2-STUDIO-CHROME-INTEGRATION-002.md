---
task_id: TASK-W7-D2-STUDIO-CHROME-INTEGRATION-002
change_id: studio-chrome-extension-integration
status: completed
assignee: codearts_agent
reviewer: claude_code
primary_skill: javascript
support_skills: ["chrome_extension", "api_integration", "testing"]
acceptance_commands: "pytest tests/integration/test_studio_integration.py -v"
created_at: 2026-04-25T10:00:00
estimated_hours: 2.0
priority: P1
depends_on: []
---

# TASK-W7-D2-STUDIO-CHROME-INTEGRATION-002

## 任务描述

将 NotebookLM Studio 真实调用集成到 Chrome Extension Popup UI，支持一键生成 Audio/Video/Slides 多模态产物。

## 背景

当前 Studio 产物生成仅支持 Backend API Mock 模式，需要在 Chrome Extension 中实现真实调用流程。

## 详细任务

### Task 1: Popup UI Studio 面板 (40min)

**位置**: `chrome-extension/public/popup.html`, `chrome-extension/public/popup.js`

**新增 UI 元素**:

```html
<!-- Studio 产物生成面板 -->
<div id="studio-panel" class="panel">
  <h3>Studio 产物生成</h3>
  <div class="studio-options">
    <label><input type="checkbox" id="studio-audio" /> Audio 播客</label>
    <label><input type="checkbox" id="studio-video" /> Video 视频</label>
    <label><input type="checkbox" id="studio-slides" /> Slides 幻灯片</label>
  </div>
  <div class="studio-focus">
    <input type="text" id="studio-focus-text" placeholder="生成主题焦点" />
  </div>
  <button id="generate-studio-btn" class="btn-primary">生成 Studio 产物</button>
  <div id="studio-status" class="status-area"></div>
</div>
```

**新增 JavaScript 函数**:

```javascript
async function generateStudioArtifacts() {
  const selectedTypes = getSelectedStudioTypes();
  const focusText = document.getElementById('studio-focus-text').value;

  const response = await chrome.runtime.sendMessage({
    type: 'GENERATE_STUDIO_ARTIFACTS',
    notebookId: currentNotebookId,
    contentTypes: selectedTypes,
    focus: focusText
  });

  displayStudioStatus(response.artifacts);
}
```

---

### Task 2: Service Worker 消息处理 (30min)

**位置**: `chrome-extension/src/background/service-worker.js`

**新增消息类型**:

```javascript
case 'GENERATE_STUDIO_ARTIFACTS':
  const bridge = new NotebookLMPackExecutorBridge();
  const artifacts = [];

  for (const contentType of request.contentTypes) {
    const result = await bridge.generateArtifact(
      request.notebookId,
      contentType,
      { focus: request.focus, language: 'zh-CN' }
    );
    artifacts.push(result);
  }

  sendResponse({ success: true, artifacts });
  break;
```

---

### Task 3: Bridge 真实调用实现 (40min)

**位置**: `chrome-extension/src/background/notebooklm-packexecutor-bridge.js`

**修改 generateArtifact() 方法**:

```javascript
async generateArtifact(notebookId, contentType, options = {}) {
  // 尝试真实调用
  try {
    const artifactId = await this._generateViaBackendAPI(notebookId, contentType, options);

    // 检查生成状态
    await this._waitForArtifactCompletion(artifactId);

    return {
      success: true,
      artifact_id: artifactId,
      mode: 'real',
      download_url: await this._getDownloadUrl(artifactId)
    };
  } catch (error) {
    // Fallback to mock
    return this._generateMockArtifact(contentType, options);
  }
}
```

---

### Task 4: 集成测试 (30min)

**位置**: `tests/integration/test_studio_integration.py`

**测试用例**:

```python
def test_studio_audio_generation():
    """测试 Audio 产物生成"""
    response = client.post('/api/notebooklm/generate',
        json={'content_type': 'audio', 'notebook_id': NOTEBOOK_ID})
    assert response.json()['success']

def test_studio_video_generation():
    """测试 Video 产物生成"""
    pass

def test_studio_slides_generation():
    """测试 Slides 产物生成"""
    pass

def test_studio_batch_generation():
    """测试批量生成 Audio + Video + Slides"""
    pass

def test_artifact_download():
    """测试产物下载"""
    pass
```

---

## 验收标准

| 标准 | 验证方法 |
|------|----------|
| Popup 显示 Studio 面板 | UI 截图验证 |
| 可选择 Audio/Video/Slides 类型 | checkbox 交互验证 |
| 点击按钮触发真实生成 | Backend API 日志验证 |
| 生成状态实时显示 | status area 更新验证 |
| 产物下载链接可点击 | download_url 验证 |
| Mock fallback 正常工作 | 断网测试验证 |

---

## 文件清单

| 文件 | 操作 |
|------|------|
| `chrome-extension/public/popup.html` | 新增 Studio 面板 UI |
| `chrome-extension/public/popup.js` | 新增 generateStudioArtifacts() |
| `chrome-extension/src/background/service-worker.js` | 新增 GENERATE_STUDIO_ARTIFACTS 消息处理 |
| `chrome-extension/src/background/notebooklm-packexecutor-bridge.js` | 完善 generateArtifact() 真实调用 |
| `tests/integration/test_studio_integration.py` | 新建集成测试 |

---

## 风险/回滚

| 风险 | 影响 | 缓解 |
|------|------|------|
| NotebookLM API 限流 | 生成失败 | 队列 + 重试机制 |
| 产物生成时间长 | UI 卡住 | 异步生成 + 进度显示 |
| 大文件下载失败 | 产物丢失 | 分块下载 + 断点续传 |

**回滚方案**: 隐藏 Studio 面板，恢复 Mock 模式

---

## 参考文档

- Studio 融合测试报告: `collaboration/results/STUDIO_FUSION_TEST_2026-04-25.md`
- NotebookLM API: `local-backend/app/api/notebooklm.py`
- Bridge 文件: `chrome-extension/src/background/notebooklm-packexecutor-bridge.js`

---

**创建时间**: 2026-04-25T10:00:00+08:00