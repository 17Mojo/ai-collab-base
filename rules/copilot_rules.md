# GitHub Copilot AI 协作系统规则 - VSCode 集成版

## 版本信息
- **版本**: v2.0.1
- **生效日期**: 2026-02-25 → 2026-02-27 (更新)
- **适配环境**: Visual Studio Code + GitHub Copilot 扩展

## 激活方式

### 任务队列自动激活（优先级最高）
当 Copilot 激活时，**必须先读取 `rules/copilot_tasks.md`**：
1. 检查是否有 PENDING 状态的独立任务
2. 按优先级从高到低执行
3. 完成后更新任务状态为 COMPLETED
4. 将结果写入指定的交接文件

这是为独立网络研究任务设计的机制，支持：
- 读取研究需求
- 执行网络请求（使用 curl）
- 整理研究结果
- 创建交接文件给 Claude

### VSCode 命令激活
当用户通过 VSCode 任务运行 `AI Collab: Activate Copilot` 或在输入中包含 `2X` 时：
```
Copilot ACK: 记忆已激活，已读取 {规则文件列表}，准备执行。
```

### 自动激活（智能补全模式）
Copilot 在以下场景自动进入协作模式：
- 用户请求代码补全时检查项目配置
- 批量修改文件时触发冲突检测
- 生成代码后自动记录到协作日志

## 执行规则

### 1. 读取规范
启动时依次加载：
- `.vscode/ai-collab.json`（项目配置）
- `rules/copilot_rules.md`（Copilot 规则）
- `rules/AI-COLLABORATION-STANDARDS.md`（协作规范）
- `rules/dev-record-template.md`（日志模板）

### 2. 执行流程
```
Preflight → Plan → Implement → Validate → Record → Report
```

| 阶段 | 说明 | VSCode 交互 |
|------|------|-------------|
| Preflight | 检查冲突状态、读取项目配置 | 读取 `.vscode/ai-collab.json` |
| Plan | 分析代码上下文、生成补全方案 | 获取编辑器上下文信息 |
| Implement | 提供代码建议、生成补全代码 | 内联补全或面板展示 |
| Validate | 验证补全代码的语法和语义 | 使用语言服务验证 |
| Record | 记录补全历史和用户接受情况 | 自动写入日志 |
| Report | 报告补统效率和用户满意度 | 可选输出面板 |

### 3. 网络研究能力（新增）

#### 网络请求方法
Copilot 可以通过以下方式执行网络请求：

```bash
# 获取 JSON API 数据
curl -s "https://api.github.com/users/github"

# 获取网页内容（解析 HTML）
curl -s "https://httpbin.org/html" | grep -E "<h1>|<title>"

# 测试网络连通性
curl -I "https://example.com"

# 获取元数据信息
curl -s "https://httpbin.org/get"
```

#### 网络研究工作流
1. **识别研究需求**: 从 `copilot_tasks.md` 读取任务描述
2. **设计请求**: 根据需求使用合适的 curl 命令
3. **执行请求**: 通过 Bash 工具执行 curl
4. **解析结果**: 提取关键信息并整理
5. **生成报告**: 创建交接文件给 Claude

#### 可用的网络服务
| 服务 | 用途 | 示例 |
|------|------|------|
| GitHub API | 获取仓库、用户信息 | `curl -s "https://api.github.com/repos/user/repo"` |
| HTTPBin | 测试网络请求 | `curl -s "https://httpbin.org/get"` |
| REST API | 获取结构化数据 | `curl -s "https://api.example.com/data"` |
| JSON API | 解析 JSON 响应 | `curl -s "url" \| jq .` |

### 4. 日志要求

#### 日志位置（三重存储）
1. **项目本地**: `logs/copilot/YYYY-MM/YYYY-MM-DD_<task>.md`
2. **Git 追踪**: `.git/ai-collab/copilot/YYYY-MM-DD_<task>.md`
3. **VSCode 输出**: `~/.vscode/ai-collab/output_YYYYMMDD.log`

#### 日志格式
必须包含：
- 补全请求上下文（文件路径、光标位置）
- 建议代码内容
- 用户接受/拒绝情况
- 网络研究结果（如适用）
- 成功率统计

### 5. 冲突检测

#### 检测时机
- **补全时**: 检查目标文件是否被 Claude Code 占用
- **应用时**: 接受建议前检查文件状态

#### 检测规则
1. 读取 `.vscode/ai-collab.json` 获取项目级状态
2. 检查 Claude Code 是否正在修改相同文件
3. 如果状态为 `implementing` 或 `testing`，暂缓建议
4. 在 VSCode 状态栏显示冲突警告

#### 冲突处理
```typescript
// [AI CONFLICT INFO]
// Claude Code 正在修改此文件
// 建议等待完成后再使用 Copilot 补全
```

### 6. VSCode 集成特性

#### 代码片段（snippets）
- `2X-copilot` 或 `copilot-activate`: 激活系统
- `ai-task`: 任务头部注释
- `conflict-mark`: 冲突标记

#### 任务（tasks）
- `AI Collab: Activate Copilot`: 激活系统
- `AI Collab: Check Conflicts`: 检查冲突
- `AI Collab: Show Copilot Statistics`: 显示统计信息

#### 状态栏集成
显示当前协作状态：
- `AI Collab: Copilot Ready` - 可用
- `AI Collab: Claude Working` - 等待中
- `AI Collab: Conflict Detected` - 冲突

### 7. 与 Claude Code 协作

#### 职责划分
| 功能 | Claude Code | Copilot |
|------|-------------|---------|
| 代码架构 | ✓ | - |
| 单元测试 | ✓ | - |
| 文档生成 | ✓ | - |
| 代码补全 | - | ✓ |
| 代码优化 | ✓ | ✓ |
| 错误修复 | ✓ | ✓ |
| 重复代码检测 | - | ✓ |
| **网络研究** | ❌ | ✓ (curl) |

#### 协作流程
1. Claude Code 设计架构并实现核心逻辑
2. Copilot 提供局部代码补全和优化建议
3. Copilot 执行网络研究任务（如需要）
4. 用户接受 Copilot 建议后，Copilot 记录变更
5. 通过 Git 追踪查看双方贡献

## 允许行为
- ✓ 读取 Claude Code 生成的代码并提供补全
- ✓ 在 Claude Code 完成的函数内添加细节实现
- ✓ 建议优化 Claude Code 编写的代码
- ✓ 生成测试用例辅助验证
- ✓ 自动补全重复代码模式
- ✓ **使用 curl 执行网络请求**

## 禁止行为
- ❌ 在 Claude Code 正在编辑的文件中提供补全
- ❌ 修改 Claude Code 标记的冲突区域
- ❌ 覆盖 Claude Code 的架构决策
- ❌ 在用户未确认时自动应用代码
- ❌ 不记录补全建议和结果
- ❌ 滥用网络请求（大量、不必要的请求）

## 质量门控
- 补全代码必须通过语法检查
- 建议必须符合项目编码规范
- 补统成功率应保持在合理范围
- 所有冲突必须妥善处理
- 网络结果必须经过验证

## 统计指标

### 日志记录指标
```json
{
  "session_id": "copilot_20260225_103000",
  "suggestions_made": 45,
  "suggestions_accepted": 38,
  "acceptance_rate": 0.84,
  "conflicts_detected": 2,
  "files_modified": 8,
  "network_requests": 3
}
```

### 每日报告
- 补统建议总数
- 接受率统计
- 冲突次数
- 覆盖文件数
- 网络请求数
- 用户满意度（可选）

## VSCode 配置项

### .vscode/settings.json
```json
{
  "aiCollab.rulesDir": "./rules",
  "aiCollab.conflictCheckOnSave": true,
  "aiCollab.showOutputPanel": true,
  "aiCollab.enableCopilotIntegration": true,
  "aiCollab.enableNetworkResearch": true,
  "github.copilot.enable": {
    "*": true,
    "yaml": false,
    "plaintext": false
  }
}
```

### .vscode/ai-collab.json
```json
{
  "version": "2.0.1",
  "rulesDir": "./rules",
  "stateFile": "./logs/collaboration_state.json",
  "enabledAIs": ["claude_code", "copilot"],
  "copilot": {
    "logSuggestions": true,
    "checkConflicts": true,
    "waitForClaude": true,
    "networkRequestsEnabled": true
  }
}
```

## 最佳实践

### 1. 充分利用上下文
- 提供清晰的注释说明意图
- 遵循命名规范让 Copilot 理解代码
- 保持函数短小精简

### 2. 合理配置
- 启用冲突检测避免覆盖
- 记录补全历史追踪变更
- 定期清理旧日志

### 3. 协作默契
- 尊重 Claude Code 的架构决策
- 在合适时机提供补全建议
- 主动等待冲突解除

### 4. 网络研究（新增）
- 仅在必要时执行网络请求
- 验证响应数据的完整性
- 缓存可重用的结果
- 保护隐私和敏感信息

## 补充规则

### 编辑器绑定
```jsonc
{
  "key": "ctrl+shift+alt+c",
  "command": "aiCollab.checkConflicts",
  "when": "editorTextFocus"
}
```

### 网络请求示例
```bash
# 获取 GitHub 仓库信息
curl -s "https://api.github.com/repos/owner/repo"

# 搜索包信息
curl -s "https://pypi.org/pypi/package-name/json"

# 测试 API 健康检查
curl -I "https://api.example.com/health"

# 获取元数据
curl -s "https://httpbin.org/uuid"
```

## 回通知响应机制

### 检测 Claude 的回通知

当 Copilot 完成交接后，需要检测 Claude 是否已接收：

```python
# 轮询检测（每 10 秒检查一次）
def check_handoff_status():
    status_file = "handoff_status.json"
    status = read_json(status_file)

    # 检测到 Claude 的回通知
    if status.get("status") == "RECEIVED_AND_PROCESSING":
        # Copilot 的响应动作
        respond_to_acknowledgement(status)
        return True

    return False
```

### 交接状态完整生命周期

```
COMPLETED (Copilot 完成)
    ↓
RECEIVED_AND_PROCESSING (Claude 读取并通知)
    ↓
HANDOFF_COMPLETE (Copilot 确认接收)
    ↓
Claude 继续工作，Copilot 待命
```

---

**版本历史**:
- v2.0.1 (2026-02-27): 新增 curl 网络研究能力
- v2.0.0 (2026-02-25): VSCode 集成初始版本
