# Week 1 剩余开发任务

**任务 ID**: TASK-WEEK1-BACKLOG-001
**变更 ID**: TASK-TD-WEEK1-BACKLOG
**状态**: pending
**assignee**: codearts_agent
**执行者**: codearts_agent
**创建时间**: 2026-04-04T10:30:00
**预估工期**: 4 小时

---

## 任务概述

完成 Week 1 剩余的开发工作，包括：
1. Pack Schema 验收测试框架完善
2. CLI Pack 管理工具增强
3. Context 持久化存储 API 集成

---

## 详细任务

### 任务 1: Pack Schema 验收测试框架完善 (1.5h)

**位置**: `tests/unit/test_schema_v2.py`

**要求**:
- 增加边界场景测试（空值、超长字符串、特殊字符）
- 增加性能测试（大 Pack 序列化/反序列化）
- 测试覆盖率提升至 90%+
- 修复发现的 Schema Bug（如有）

**验收标准**:
```bash
pytest tests/unit/test_schema_v2.py --cov=src.ai_collab/pack/schema_v2 --cov-report=term
# coverage >= 90%
# 所有测试通过
```

**交付物**:
- 更新的测试文件
- 测试报告

---

### 任务 2: CLI Pack 管理工具增强 (2h)

**位置**: `ai_collab/cli.py`

**新增命令**:

1. `pack validate` - 验证 Pack 合法性
   - 参数: `--path PACK_FILE`
   - 功能: JSON 语法验证、必需字段检查、Schema 合规性

2. `pack template` - 生成 Pack 模板
   - 参数: `--name NAME --category CATEGORY`
   - 功能: 生成完整 Pack 模板 JSON

3. `pack export/import` - Pack 导入导出
   - 参数: `--export/--import SOURCE_PATH`
   - 功能: Pack 文件的导入导出

**验收标准**:
```bash
# 测试所有新命令
python -m ai_collab.cli pack validate --path packs/examples/xiaohongshu_beauty_review.json
python -m ai_collab.cli pack template --name demo --category content_generation
python -m ai_collab.cli pack export --source packs/examples/demo.json
python -m ai_collab.cli pack import --source packs/demo.json
```

**交付物**:
- 更新的 `cli.py`
- 命令帮助文档

---

### 任务 3: Context 持久化存储 API 集成 (0.5h)

**位置**: `local-backend/app/api/context.py`

**要求**:
- 替换 `_in_memory_storage` 为 SQLAlchemy 数据库操作
- 集成 `local-backend/app/models/context.py` 中的模型
- 添加数据库初始化代码

**验收标准**:
- API 端点正常工作
- 数据持久化到 SQLite
- 重启后数据保持

**交付物**:
- 更新的 API 端点
- 数据库初始化脚本

---

## 执行步骤

1. 先执行任务 1（测试框架）
2. 再执行任务 2（CLI 工具）
3. 最后执行任务 3（持久化集成）
4. 每个子任务完成后更新进度到结果文件

---

## 心跳要求

每 30 分钟更新一次进度到结果文件，包含：
- 当前步骤
- 完成情况
- 阻塞问题
- 下一步计划

---

## 验收标准

- ✅ 所有测试通过
- ✅ 所有 CLI 命令可用
- ✅ Context 可持久化
- ✅ 结果文件完整

---

**创建人**: Claude (Technical Partner)
**审核人**: 待定
**优先级**: P0
