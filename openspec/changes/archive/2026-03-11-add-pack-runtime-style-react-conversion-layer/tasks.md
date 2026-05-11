# Tasks

## 1. Runtime Style Overrides (UI + Protocol)
- [x] 1.1 在 Popup 增加运行时微调字段（style_profile/tone/length/compliance_level/temperature_bias）
- [x] 1.2 扩展 `executePack` 请求体，透传 `runtime_overrides`
- [x] 1.3 在 message-handler/executor 合并覆盖参数并保持默认兼容
- [x] 1.4 增加非法覆盖参数的回退与日志

## 2. ReAct Requirement Conversion Layer
- [x] 2.1 实现 Owner 自然语言需求到 ReAct 步骤化转换入口
- [x] 2.2 产出标准转换产物（draft_pack/change_manifest/validation_report）
- [x] 2.3 实现跨 Pack 元素检索与继承映射规则
- [x] 2.4 增加冲突检测与合规风险提示

## 3. Validation Gates
- [x] 3.1 接入 `PromptPackV2.from_dict` 与 `validate()` 结构闸
- [x] 3.2 增加业务合规闸（规则覆盖、禁用词、行业指标）
- [x] 3.3 保证运行时覆盖不回写基线 JSON

## 4. Tests & CI
- [x] 4.1 新增单测：runtime_overrides 白名单、边界、优先级
- [x] 4.2 新增单测：ReAct 转换层输出结构与校验结果
- [x] 4.3 新增集成测：Popup -> Content -> Executor 协议透传
- [x] 4.4 新增 E2E：扩展宿主 mock 下覆盖执行链路（避免 chrome.storage 假阳性）

## 5. Quality Gates
- [x] 5.1 `openspec validate add-pack-runtime-style-react-conversion-layer --strict`
- [x] 5.2 `python3 -m pytest -q tests/unit/test_pack_requirement_conversion.py tests/unit/test_schema_v2.py`
- [x] 5.3 `python3 -m pytest -q tests/e2e/test_prompt_pack_runtime_overrides.py`
- [x] 5.4 `python3 -m ai_collab.cli tasks validate-contract --scope all --strict`
