# TASK-W3-DAY2-BULK-OPERATIONS-001

Week 3 Day 2: Pack 批量操作

---

## 任务信息

- **Task ID**: `TASK-W3-DAY2-BULK-OPERATIONS-001`
- **优先级**: P0
- **复杂度**: 中
- **预计耗时**: 1.5h
- **负责人**: claude_code
- **状态**: implementing

---

## 任务描述

实现 Pack 批量操作功能，支持：
1. 批量创建 Pack
2. 批量更新版本
3. 批量归档
4. 批量删除 (带确认)

## 实现要求

### 1. 数据模型 ([src/ai_collab/pack/bulk.py](src/ai_collab/pack/bulk.py))

**核心类**:

```python
@dataclass
class BulkOperation:
    """批量操作"""
    operation_type: str  # create/update/archive/delete
    pack_ids: List[str]
    status: str  # pending/running/completed/failed
    results: List[Dict[str, Any]]
    created_at: str
    updated_at: str

class BulkOperationResult:
    """批量操作结果"""
    operation_id: str
    total: int
    succeeded: int
    failed: int
    results: List[Dict[str, Any]]
```

**核心引擎**:

```python
class BulkOperationEngine:
    """批量操作引擎"""

    def bulk_create(self, pack_specs: List[Dict]) -> BulkOperationResult
    def bulk_update_version(self, pack_ids: List[str], version_bump: str) -> BulkOperationResult
    def bulk_archive(self, pack_ids: List[str]) -> BulkOperationResult
    def bulk_delete(self, pack_ids: List[str], confirm_token: str) -> BulkOperationResult
    def get_operation_status(self, operation_id: str) -> BulkOperationResult
```

### 2. CLI 命令 ([ai_collab/cli/pack_bulk.py](ai_collab/cli/pack_bulk.py))

**命令**:
```bash
# 批量创建
python3 ai_collab/cli/pack_bulk.py create --specs specs.json [--parallel]

# 批量更新版本
python3 ai_collab/cli/pack_bulk.py update-version --pack-ids pack1,pack2 --bump patch

# 批量归档
python3 ai_collab/cli/pack_bulk.py archive --pack-ids pack1,pack2,pack3

# 批量删除
python3 ai_collab/cli/pack_bulk.py delete --pack-ids pack1,pack2 --confirm TOKEN

# 查看操作状态
python3 ai_collab/cli/pack_bulk.py status <operation_id>
```

### 3. 测试 ([tests/unit/pack/test_bulk.py](tests/unit/pack/test_bulk.py))

**测试类**:

| 测试类 | 测试数量 | 覆盖内容 |
|--------|---------|---------|
| TestBulkOperation | 3 | 数据类序列化 |
| TestBulkOperationEngine | 10 | 核心操作引擎 |
| TestBulkCLI | 4 | CLI 命令功能 |

**总测试数**: 17

---

## 验收标准

- ✅ 批量操作引擎实现完整
- ✅ 原子性保证 (操作失败可回滚)
- ✅ 并发安全
- ✅ CLI 命令可用
- ✅ 测试覆盖率 >= 80%
- ✅ 所有测试通过 (17/17)

---

## 执行步骤

1. 创建批量操作引擎 `src/ai_collab/pack/bulk.py`
2. 实现原子性操作机制
3. 实现批量 CLI 命令
4. 编写测试
5. 运行验收命令

---

## 验收命令

```bash
# 运行单元测试
PYTHONPATH=. python3 -m pytest tests/unit/pack/test_bulk.py -v

# 运行覆盖率检查
PYTHONPATH=. python3 -m pytest tests/unit/pack/test_bulk.py --cov=src.ai_collab.pack.bulk --cov-report=term
```

---

## 依赖关系

- 依赖 `src/ai_collab/pack/market_api.py` (Pack 管理接口)
- 依赖 `src/ai_collab/pack/version.py` (版本管理)

---

## 预期输出

- `src/ai_collab/pack/bulk.py` (批量操作引擎)
- `ai_collab/cli/pack_bulk.py` (批量操作 CLI)
- `tests/unit/pack/test_bulk.py` (测试文件)
- `collaboration/results/RESULT_TASK-W3-DAY2-BULK-OPERATIONS-001.md` (结果报告)

---

**任务创建时间**: 2026-04-06 10:00
**任务状态**: implementing
