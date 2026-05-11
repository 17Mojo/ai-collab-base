# AI 协作开发标准规范

## 版本信息
- **版本**: v1.0.0
- **生效日期**: 2026-02-25
- **适用范围**: Claude Code 与 Trae AI 协作开发

## 1. 协作原则

### 1.1 单一职责
- 每个AI在同一时间只处理一个任务
- 任务完成后才能接受新任务
- 禁止多任务并行处理

例外说明：

- Codex 可在**单一父任务内部**使用 `spawn_agent` 进行受控委派
- 该能力不视为新增独立外部任务
- 前提是不得绕过状态、锁、写集隔离与正式 ACK/工单流程
- 对所有正式 assignee 而言，正式闭环都要求显式 ACK 证据；`receipt` / `state drift` / `missing_ack` fallback 均不能替代
- 详细规则见 `collaboration/guides/CODEX_SPAWN_AGENT_USAGE_GUIDELINES.md`

### 1.2 状态透明
- 所有任务状态必须实时同步到 `collaboration_state.json`
- 文件修改前必须检查冲突状态
- 状态变更必须记录时间戳
- `ai_type` 代表原始派单对象，`assignee`/`ownership.owner` 代表当前责任 owner；合法 takeover 后两者不一致是允许的，不能机械按“不一致”判异常

### 1.3 日志完整
- 每次开发必须生成结构化日志
- 日志必须包含：任务ID、时间、变更、结果
- 日志格式统一使用 `dev-record-template.md`

## 2. 开发前检查清单

### 2.1 Claude Code 检查项
```markdown
- [ ] 检测到激活词 `2X`
- [ ] 读取 `claude_code_memory.md`
- [ ] 读取 `AI-COLLABORATION-STANDARDS.md`
- [ ] 检查 `collaboration_state.json` 冲突状态
- [ ] 确认目标文件未被标记为 `implementing` 或 `testing`
- [ ] 创建开发日志文件
```

### 2.2 Trae AI 检查项
```markdown
- [ ] 检测到激活词 `2X`
- [ ] 读取 `trae_rules.md`
- [ ] 读取 `AI-COLLABORATION-STANDARDS.md`
- [ ] 检查 `collaboration_state.json` 冲突状态
- [ ] 确认目标文件未被标记为 `implementing` 或 `testing`
- [ ] 创建开发日志文件
```

## 3. 冲突解决机制

### 3.1 冲突检测
当AI尝试修改文件时，系统检查：
1. 目标文件是否存在于其他任务的 `files` 列表中
2. 对应任务状态是否为 `implementing` 或 `testing`
3. 如果是，标记为冲突并阻止操作

### 3.2 冲突解决流程
```
检测到冲突
    ↓
暂停当前操作
    ↓
通知用户冲突详情
    ↓
等待用户决策
    ↓
执行用户选择方案
```

### 3.3 用户决策选项
- **选项A**: 等待其他任务完成后再执行
- **选项B**: 取消其他任务，优先执行当前任务
- **选项C**: 合并修改（仅适用于非冲突行）
- **选项D**: 手动指定文件分区，各自修改不同部分

## 4. 禁止行为列表

### 4.1 通用禁止
- ❌ 不读取规则直接开始开发
- ❌ 不检查冲突状态直接修改文件
- ❌ 不记录开发日志
- ❌ 同时处理多个未关联的任务
- ❌ 修改标记为 `conflict` 的文件
- ❌ 删除或修改其他AI的日志文件
- ❌ 绕过状态检查机制

### 4.2 Claude Code 特有禁止
- ❌ 跳过 `Test` 阶段直接标记完成
- ❌ 不生成测试覆盖报告

### 4.3 Trae AI 特有禁止
- ❌ 跳过 `Validate` 阶段直接标记完成
- ❌ 不生成验证报告

## 5. 质量门控标准

### 5.1 代码质量
- 所有代码必须通过类型检查
- 所有函数必须有类型注解
- 所有复杂逻辑必须有注释

### 5.2 测试覆盖
- 新功能必须有对应的测试用例
- 测试覆盖率不得低于80%
- 所有测试必须通过才能标记完成

### 5.3 文档要求
- 所有公共API必须有文档字符串
- 所有配置文件必须有注释说明
- 所有变更必须在日志中记录

## 6. 状态定义

### 6.1 任务状态
- `pending`: 任务已创建，等待执行
- `planning`: 正在制定执行计划
- `implementing`: 正在实现代码
- `testing`: 正在测试/验证
- `completed`: 任务已完成
- `failed`: 任务执行失败
- `cancelled`: 任务已取消

### 6.2 文件状态
- `clean`: 文件未被修改
- `modified`: 文件已被修改但未提交
- `conflict`: 文件存在冲突
- `locked`: 文件被锁定，禁止修改

## 7. 日志规范

### 7.1 日志位置
- Claude Code: `logs/claude-code/YYYY-MM/YYYY-MM-DD_<task>.md`
- Trae AI: `logs/trae-ai/YYYY-MM/YYYY-MM-DD_<task>.md`

### 7.2 日志内容
必须包含以下章节：
1. 任务信息（ID、描述、时间）
2. 执行计划
3. 执行过程记录
4. 变更文件列表
5. 测试/验证结果
6. 问题与解决方案
7. 总结与下一步

### 7.3 时间戳格式
- 日期: `YYYY-MM-DD`
- 时间: `HH:MM:SS`
- 完整格式: `YYYY-MM-DD HH:MM:SS`

## 8. 应急处理

### 8.1 系统故障
如果状态文件损坏或丢失：
1. 立即停止所有开发活动
2. 从备份恢复状态文件
3. 如果无备份，重新初始化状态
4. 通知用户故障情况

### 8.2 冲突升级
如果冲突无法自动解决：
1. 标记冲突为 `unresolved`
2. 记录冲突详情到 `collaboration_issues.json`
3. 通知用户手动介入
4. 等待用户决策

## 9. 附录

### 9.1 文件清单
| 文件 | 作用 |
|------|------|
| `claude_code_memory.md` | Claude Code系统提示词 |
| `trae_rules.md` | Trae AI系统提示词 |
| `AI-COLLABORATION-STANDARDS.md` | 协作规范 |
| `dev-record-template.md` | 日志模板 |
| `collaboration_state.json` | 协作状态 |
| `collaboration_issues.json` | 问题记录 |

### 9.2 更新记录
| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0.0 | 2026-02-25 | 初始版本 |
