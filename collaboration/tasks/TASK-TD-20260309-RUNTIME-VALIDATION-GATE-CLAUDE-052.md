# 任务: Runtime 覆盖白名单与合规双闸实现

**任务ID**: TASK-TD-20260309-RUNTIME-VALIDATION-GATE-CLAUDE-052  
**change_id**: add-pack-runtime-style-react-conversion-layer  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P0

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [api-test-pro, systematic-debugging]
- **scope_in**: 为 runtime_overrides 增加白名单与边界校验，并接入 schema + 业务合规双闸判定。
- **scope_out**: 不新增行业策略引擎，不引入新外部依赖。

## 输入

- 文件:
  - `openspec/changes/add-pack-runtime-style-react-conversion-layer/specs/prompt-pack-runtime-style/spec.md`
  - `openspec/changes/add-pack-runtime-style-react-conversion-layer/specs/pack-requirement-conversion/spec.md`
  - `products/prompt-pack-extension/chrome/src/content/pack-executor.js`
  - `src/ai_collab/pack/schema_v2.py`
  - `research/reverse-engineering/PACK_CROSS_INDUSTRY_FIELD_MAPPING_MATRIX_2026-03-09.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260309-RUNTIME-VALIDATION-GATE-CLAUDE-052.md`
- 必须包含:
  - 白名单字段与非法输入处理策略
  - 双闸通过/失败样例
  - 不回写基线 JSON 的验证证据
  - 回滚策略

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/e2e/test_prompt_pack_runtime_overrides.py
python3 -m pytest -q tests/unit/test_pack_requirement_conversion.py
python3 -m pytest -q tests/unit/test_schema_v2.py
openspec validate add-pack-runtime-style-react-conversion-layer --strict
```

## 状态

- [x] pending
- [ ] planning
- [ ] implementing
- [ ] testing
- [ ] blocked
- [ ] completed
- [ ] failed
- [ ] cancelled
