# TASK-W3-DAY1-PACK-DEPENDENCY-001

Week 3 Day 1: Pack 依赖管理系统

---

## 任务信息

- **Task ID**: `TASK-W3-DAY1-PACK-DEPENDENCY-001`
- **优先级**: P0
- **复杂度**: 中
- **预计耗时**: 2h
- **负责人**: claude_code
- **状态**: pending

---

## 任务描述

实现 Pack 依赖管理系统，支持：
1. 依赖声明数据结构
2. 依赖解析算法 (基于 SemVer)
3. 依赖冲突检测
4. 版本兼容性检查

---

## 实现要求

### 1. 数据模型 ([src/ai_collab/pack/dependency.py](src/ai_collab/pack/dependency.py))

**核心类**:

```python
@dataclass
class PackDependency:
    """Pack 依赖定义"""
    name: str
    version_range: str  # SemVer range (e.g., ">=1.0.0,<2.0.0")
    optional: bool = False
    reason: str = ""

    def is_compatible_with(self, version: str) -> bool
    def to_dict(self) -> Dict[str, Any]

@dataclass
class DependencyNode:
    """依赖图节点"""
    pack_id: str
    version: str
    dependencies: List[PackDependency]
    resolved: bool = False

@dataclass
class DependencyResult:
    """依赖解析结果"""
    success: bool
    resolved: List[DependencyNode]
    conflicts: List[Dict[str, Any]]
    errors: List[str]
```

**核心算法**:

```python
class DependencyResolver:
    """依赖解析器"""

    def resolve(self, root: DependencyNode) -> DependencyResult:
        """解析依赖树"""

    def detect_conflicts(self, graph: List[DependencyNode]) -> List[Dict[str, Any]]:
        """检测依赖冲突"""

    def check_compatibility(self, dep: PackDependency, version: str) -> bool:
        """检查版本兼容性"""

    def topo_sort(self, graph: List[DependencyNode]) -> List[DependencyNode]:
        """拓扑排序，确定加载顺序"""
```

---

### 2. CLI 命令 ([ai_collab/cli/pack_dependency.py](ai_collab/cli/pack_dependency.py))

**命令**:
```bash
# 添加依赖
python3 ai_collab/cli/pack_dependency.py add <pack_id> <dep_name> --version ">=1.0.0"

# 列出依赖
python3 ai_collab/cli/pack_dependency.py list <pack_id>

# 解析依赖树
python3 ai_collab/cli/pack_dependency.py resolve <pack_id>

# 删除依赖
python3 ai_collab/cli/pack_dependency.py remove <pack_id> <dep_name>

# 检查冲突
python3 ai_collab/cli/pack_dependency.py check <pack_id>
```

---

### 3. 测试 ([tests/unit/pack/test_dependency.py](tests/unit/pack/test_dependency.py))

**测试类**:

| 测试类 | 测试数量 | 覆盖内容 |
|--------|---------|---------|
| TestPackDependency | 3 | 依赖数据序列化/反序列化 |
| TestSemVerCompatibility | 5 | 版本范围解析和兼容性检查 |
| TestDependencyResolver | 8 | 依赖解析、冲突检测、拓扑排序 |
| TestCLICommands | 4 | CLI 命令功能 |

**总测试数**: 20

---

## 验收标准

- ✅ 数据模型实现完整
- ✅ 依赖解析算法正确
- ✅ 冲突检测无遗漏
- ✅ CLI 命令可用
- ✅ 测试覆盖率 ≥ 80%
- ✅ 所有测试通过 (20/20)

---

## 执行步骤

1. 创建数据模型文件 `src/ai_collab/pack/dependency.py`
2. 实现 SemVer 版本范围解析
3. 实现依赖解析算法
4. 实现冲突检测
5. 创建 CLI 命令
6. 编写测试
7. 运行验收命令

---

## 验收命令

```bash
# 运行单元测试
pytest tests/unit/pack/test_dependency.py -v

# 运行覆盖率检查
pytest tests/unit/pack/test_dependency.py --cov=src.ai_collab.pack.dependency --cov-report=term
```

---

## 依赖关系

- 依赖 `src/ai_collab/pack/version.py` (SemVer 实现)
- 依赖 `src/ai_collab/pack/schema_v2.py` (Pack 数据结构)

---

## 预期输出

- `src/ai_collab/pack/dependency.py` (依赖管理核心)
- `ai_collab/cli/pack_dependency.py` (依赖 CLI 命令)
- `tests/unit/pack/test_dependency.py` (测试文件)
- `collaboration/results/RESULT_TASK-W3-DAY1-PACK-DEPENDENCY-001.md` (结果报告)

---

**任务创建时间**: 2026-04-05 19:45
**任务状态**: pending
