---
task_id: TASK-W8-D4-PACK-SAMPLE-VALIDATION-004
change_id: pack-sample-compatibility-validation
status: completed
assignee: codearts_agent
reviewer: claude_code
primary_skill: testing
support_skills: ["python", "javascript", "json_validation"]
acceptance_commands: "pytest tests/integration/test_pack_validation.py -v"
created_at: 2026-04-26T09:00:00
estimated_hours: 2.0
priority: P1
depends_on: ["TASK-W7-D1-BRANCH-REGEX-IMPL-001"]
---

# TASK-W8-D4-PACK-SAMPLE-VALIDATION-004

## 任务描述

验证所有 17 个 Pack 示例与 Schema v2.0 的兼容性，确保无分支字段的 Pack 继续顺序执行。

## 背景

Week 7 新增了分支逻辑字段，需要验证现有 Pack 示例不会因 Schema 变更而失效。

## 详细任务

### Task 1: 创建 Pack 验证测试 (30min)

**位置**: `tests/integration/test_pack_validation.py`

**测试用例**:

```python
import json
from pathlib import Path

PACK_DIR = Path("packs/examples")

def test_all_packs_load_success():
    """验证所有 Pack 可正常加载"""
    for pack_file in PACK_DIR.glob "*.json":
        with open(pack_file) as f:
            data = json.load(f)
        assert "metadata" in data
        assert "workflow" in data

def test_schema_v2_compatibility():
    """验证 Schema v2.0 兼容性"""
    from src.ai_collab.pack.schema_v2 import PromptPackV2

    for pack_file in PACK_DIR.glob "*.json":
        with open(pack_file) as f:
            data = json.load(f)
        # 尝试解析为 PromptPackV2
        pack = PromptPackV2.from_dict(data)
        assert pack.validate()

def test_backward_compatibility():
    """验证向后兼容 - 无分支 Pack 顺序执行"""
    # 加载无 branches 字段的 Pack
    simple_pack = PACK_DIR / "demo-pack.json"
    with open(simple_pack) as f:
        data = json.load(f)

    # 验证 step 没有 branches 字段
    for step in data["workflow"]["steps"]:
        assert "branches" not in step or step.get("branches") is None

def test_branch_pack_structure():
    """验证带分支 Pack 结构正确"""
    branch_pack = PACK_DIR / "error-handling-workflow.json"
    with open(branch_pack) as f:
        data = json.load(f)

    # 验证分支目标步骤存在
    step_ids = {s["id"] for s in data["workflow"]["steps"]}
    for step in data["workflow"]["steps"]:
        if step.get("branches"):
            for branch in step["branches"]:
                assert branch["target_step"] in step_ids
```

---

### Task 2: 逐个 Pack 验证 (45min)

**验证清单**:

| Pack | 验证项 | 状态 |
|------|--------|------|
| ai_collab_intro.json | Schema 兼容 | ⏳ |
| bilibili_video_script.json | Schema 兼容 | ⏳ |
| demo-pack.json | 顺序执行 | ⏳ |
| douyin_video_script.json | Schema 兼容 | ⏳ |
| email-auto-reply.json | Schema 兼容 | ⏳ |
| error-handling-workflow.json | 分支验证 | ⏳ |
| generic_content_writer.json | Schema 兼容 | ⏳ |
| tech_documentation.json | Schema 兼容 | ⏳ |
| travel_planner_north_guide.json | Schema 兼容 | ⏳ |
| weekly_report.json | Schema 兼容 | ⏳ |
| weibo_explosive_copy.json | Schema 兼容 | ⏳ |
| xiaohongshu_beauty_review.json | Schema 兼容 | ⏳ |
| xiaohongshu_food_explore.json | Schema 兼容 | ⏳ |
| xiaohongshu_knowledge_creator.json | Schema 兼容 | ⏳ |
| zhihu_answer_optimization.json | Schema 兼容 | ⏳ |

---

### Task 3: 修复不兼容 Pack (30min)

如发现不兼容问题：
- 添加缺失字段 (设为 null 或默认值)
- 调整字段顺序
- 补充必填字段

---

### Task 4: 生成验证报告 (15min)

**位置**: `collaboration/results/PACK_VALIDATION_REPORT_2026-04-26.md`

**内容**:
- Pack 列表 + 验证结果
- 不兼容问题汇总
- 修复记录

---

## 验收标准

| 标准 | 验证方法 |
|------|----------|
| 17/17 Pack 加载成功 | pytest 输出 |
| Schema v2 兼容 100% | PromptPackV2.from_dict 成功 |
| 无分支 Pack 顺序执行验证 | 测试断言 |
| 分支 Pack 目标步骤验证 | 测试断言 |
| 验证报告生成 | 文件存在 |

---

## 文件清单

| 文件 | 操作 |
|------|------|
| tests/integration/test_pack_validation.py | 新建 |
| collaboration/results/PACK_VALIDATION_REPORT_2026-04-26.md | 新建 |

---

## 风险/回滚

| 风险 | 影响 | 缓解 |
|------|------|------|
| Schema 不兼容 | Pack 加载失败 | Optional 字段 + 默认值 |
| 分支目标不存在 | 执行报错 | Schema 验证目标步骤 |

---

**创建时间**: 2026-04-26T09:00:00+08:00