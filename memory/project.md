---
name: AI Collaboration System 项目状态与技术债追踪
description: AI Collaboration System 项目状态、技术债、并行协作风险与测试环境陷阱
type: project
from: Agent
---

# AI Collaboration System 项目记忆

## 项目概况
- **项目名称**: AI Collaboration System (Prompt Pack v2.0)
- **架构**: Local-first Chrome Extension + VSCode + FastAPI + SQLite
- **核心功能**: AI chat interactions 自动化
- **用户规模**: **零外部用户，完全自用**（2026-10-22 用户亲口确认）。git 近 200 提交作者全为用户本体身份（17Mojo/Raymondna）+ AI 协作者身份（AI-Collab Auditor/ai-collab/Trae AI），无外部贡献者佐证。
  - **Why**: 决定产品路线的关键输入——路线 A（Prompt Pack 面向创作者）无既有用户基础；路线 B（Agent 协作控制面产品化）的押注前提成立。
  - **How to apply**: 涉及功能取舍/路线讨论时，以"单人 + AI 协作者的自用场景"为默认用户画像；不建议为假想外部用户增加面向 C 端的复杂度；"真实用户验证"类建议对该项目指"找第一个外部用户"而非"回归已有用户"。

## 技术债与待办事项 (2026-09-19 校验)

### 高优先级
- **Schema v2.0 完成度**: ✅ **已完成**（文件头标注 `Status: COMPLETED (v2.0.0)` / `Completed: 2026-02-27`）。测试覆盖率 **96%**（305 stmts / 11 missed），110 tests pass。原记忆"60%→100% 进行中"已于 2026-09-19 校验为严重过期。

### 中优先级
- **双向交接通知**: handoff_status.json 更新机制未实现（文件 GONE，阻塞多 Agent 协作）
- **自动冲突解决**: 未实现（依赖 handoff 机制）
- **测试覆盖率**: ✅ **81% 已超目标**（2350 passed / 6 skipped，Python 3.14.6，2026-09-19 校验）
- **Schema v2.0 验证器架构债（2026-09-19 gap analysis 发现）**:
  - 🔴 **`ai_collab/pack/schema_validator.py` 527 行是孤儿代码**：`PackSchemaValidator` / `validate_pack` 仅在自身文件内被引用，`ai_collab/` / `local-backend/` / `src/` 均无业务路径调用。所有验证走 `schema_v2.py::PromptPackV2.validate()`（仅 4 项弱验证：pack_id 非空 / pack_name 非空 / steps 非空 / 步骤 ID 唯一 / 权重总和）。
  - 🟡 **双验证器脱节**：`schema_validator.py` 含 7 个 `_validate_` 子方法（更严格）但未被调用；`PromptPackV2.validate()` 4 项 vs schema_validator 7 项无一致性保证。
  - 🟡 **`PromptPackV2.validate()` 缺失检查**：SemVer 版本格式 / datetime 合理性（created_at ≤ updated_at）/ workflow 步骤引用完整性（next_step / branches.target_step / on_error / on_timeout）/ quality_metrics 权重非负 / target_platforms 非空。
  - **决策点未定（需用户确认）**: 路 A（接入 schema_validator.py 到业务路径如 `local-backend/app/api/packs.py` create/update 端点，527 行从死代码变活代码）vs 路 B（删除 schema_validator.py，合并 7 个子方法到 `PromptPackV2.validate()`）。建议先做两文件字段定义一致性 audit 再决策。
  - **Why**: gap analysis 揭示记忆严重过期（原"60%→100% 进行中"实际已 COMPLETED），但完成度仅指 dataclass 定义+序列化+测试，**验证逻辑完整性是独立维度仍有缺口**。
  - **How to apply**: 触及 Pack 验证/创建/更新路径前，先确认走的是哪个验证器；提议补 validate() 检查项时优先步骤引用完整性（影响 workflow 执行）而非 SemVer 格式（cosmetic）。

### 已解决/已清理（2026-09-19 校验确认）
- **CONFLICT-1772060801**: ✅ 已解决 — `src/cli.py` 1008 行无冲突标记；仅 `rules/OWNERSHIP_UPDATE.md` / `logs/monitoring_backup/` 文档残留引用待清
- **双源码目录差异**: ✅ 已解决 — `src/ai_collab/` 已删除
- **OWNERSHIP.md**: ✅ 已创建 — `rules/OWNERSHIP.md` EXISTS
- **Pack 示例重复文件**: ✅ 非重复 — `packs/examples/email-auto-reply.json` vs `packs/exports/email_auto_reply_export_*.json` 是 example vs export，非重复
- **Chrome 扩展重构导致 stale tests（过时测试，非路径漂移）**: ✅ 已完成并提交（2026-09-19，commit 链 `0c0e8df` → `6700c70` → `1f10c8a`）。Chrome 扩展经历了彻底重构 —— `products/prompt-pack-extension/chrome/` → 根目录 `chrome-extension/`，多文件模块化 → ESM + platform adapters + service-worker。原 `TestChromeExtensionFiles` / `TestProjectStructure` / `test_ui_accessibility` 等共 21 个测试断言的是重构**之前**已废弃的文件与功能特性（`src/content/index.js`、`storage-manager.js` AES-GCM、`enhanced-message-handler.js` retryQueue、`error-recovery.js`、`background/index.js` STORAGE_SCHEMA_VERSION、`options/options.js`、`popup/styles.css`、`products/vscode-extension/package.json`），已全部按"重写"路线对齐新架构（拒绝机械改路径 / 删除）。
  - **提交详情**:
    - `0c0e8df` `test(e2e): 重写 chrome-extension 守护类对齐新架构`（`tests/e2e/test_integration.py`）—— TestChromeExtensionFiles 16 测试 + TestProjectStructure::test_required_directories；新增 `_ext_root()` 辅助方法
    - `6700c70` `test(a11y): 重写 popup 无障碍门禁对齐 chrome-extension/ 新路径`（`tests/e2e/test_ui_accessibility.py`）—— 全文覆写；新增 `_extract_inline_style` 提取内联 `<style>` 块；硬门禁只放基线项，"语义标签缺失" 降级为软告警
    - `1f10c8a` `test(state): 修 fallback 全局目录 mock 不彻底导致断言 ai-collab 失败`（`tests/unit/test_state_manager_extra.py`）—— 统一与 `test_backup_dir_fallback_to_global` 写法（设 HOME 让 `expanduser('~')` 自然走到 tmp_path/fakehome）
    - `8a12c53` `feat(a11y): popup.html 改造语义标签 + 补充键盘焦点样式`（`chrome-extension/public/popup.html`）—— 承接 6700c70 软告警落地：4 个 `<div>` → `<header>`/`<main>`/`<section aria-labelledby>`/`<footer>`；CSS 加 `:focus-visible`/`:active` 键盘焦点；Studio 状态区 `role="status" aria-live="polite"`
    - `f275903` `test(a11y): 回填硬门禁守护语义标签与键盘焦点样式`（`tests/e2e/test_ui_accessibility.py`）—— `_chrome_html_check` 加 4 项语义标签门禁；`_chrome_css_check` 加 `:focus-visible`/`:active`；recommendations 移除已落地项
  - **验证结果（2026-09-19）**: 全量测试 **2350 passed / 0 failed / 6 skipped**（Python 3.14.6）；`ruff check tests/e2e/test_integration.py tests/e2e/test_ui_accessibility.py tests/unit/test_state_manager_extra.py` 全绿。
  - **方案决策（2026-09-19）**: 用户已选定对 stale tests 走「重写」路线（而非删除或机械改路径）。要求先彻底摸清新架构的真实结构，再写出守护真实代码的断言。test_integration 修 2 处误判：packExecutor.execute 容忍换行；service-worker 改检查独立 `settings-handler.js` 含 `handleSettingsMessage`/`GET_SETTINGS`（与真实架构一致）。a11y 把"语义标签缺失"从硬门禁降级为软告警（`recommendations` 上报），未造假断言。
  - **后续待办**: ✅ 已完成（2026-09-19，commit 链 `0c0e8df` → `6700c70` → `1f10c8a` → `8a12c53` → `f275903`）：(a) 按 `test(e2e):` / `test(a11y):` 拆分为聚焦 commit 已落地；(b) 遗留 `test_state_manager_extra::test_state_file_falls_back_to_global_dir` 已按方案 A 修复（mock 返回 `tmp/fakehome/.vscode/ai-collab` 段 + 清理未使用 `tempfile` import）并提交；(c) a11y 软告警已落地（popup.html 语义标签 + 焦点样式）+ 硬门禁回填。工作区除 `test_tracking_history.json` 临时文件外干净。
  - **修复方案 A 落地说明（2026-09-19）**：`test_state_file_falls_back_to_global_dir` 的根因是 mock 链未替换彻底 —— `state_manager.py:131` 直接调 `os.path.expanduser("~/.vscode/ai-collab")`，而测试 mock `os.path.expanduser` 返回裸 `tempfile.mkdtemp()`，最终路径不含 `ai-collab` 段。方案 A：统一两个 fallback 测试写法（mock 返回 `tmp/fakehome/.vscode/ai-collab` 段，对齐产品真证），与同文件 `test_backup_dir_fallback_to_global` 写法一致。明确拒绝方案 B（弱化断言）——后者违反"硬门禁对齐真证"原则。
  - **重写时的架构真证摸底（2026-09-19）**：在重写/校验 chrome-extension 相关测试前，必须先 grep 源码确认以下事实，避免基于错误假设写断言：
    1. `packExecutor.execute(...)` 调用因换行写成 `packExecutor\n          .execute(...)`，**字符串搜索必须容忍换行符**（如正则 `re.search(r"packExecutor\s*\.execute\s*\(", ...)`）
    2. **settings 数据流：仅 popup.js → service-worker `SETTINGS_UPDATED` 写入**；service-worker 自身**没有** `GET_SETTINGS` 处理（违反常见假设，断言 GET_SETTINGS 会被拒绝的测试会假阳性通过）
    3. **popup.html 已用语义标签**（2026-09-19 8a12c53 改造）：4 个主要分区改为 `<header>`/`<main>`/`<section aria-labelledby="studio-panel-title">`/`<footer>`；CSS 已含 `:focus-visible`/`:active` 键盘焦点样式（用 `:focus-visible` 而非 `:focus`，符合 WAI-ARIA 最佳实践）。可访问性硬门禁已回填（f275903），不再视为软告警。
    4. **settings 数据流的真实承载者**：不是 service-worker 的 message 处理器，而是独立模块 `chrome-extension/src/background/settings-handler.js`（导出 `handleSettingsMessage`、支持 `GET_SETTINGS`）。**断言要落到独立模块文件存在 + 含目标符号**，不要写"service-worker 直接处理 GET_SETTINGS"这种臆测
  - **已完成 popup.html 无障碍改造（2026-09-19，commit 链 `8a12c53` → `f275903`）**:
    - `8a12c53` `feat(a11y): popup.html 改造语义标签 + 补充键盘焦点样式` —— 4 个 `<div>`（`.header`/`.content`/`.status`/`#studio-panel`）改为 `<header>`/`<main>`/`<section>`/`<footer>`；CSS 加 `:focus-visible`/`:active` 键盘焦点样式；Studio 状态区加 `role="status" aria-live="polite"`。data-testid 全部保留不破坏 E2E 守护。
    - `f275903` `test(a11y): 回填硬门禁守护语义标签与键盘焦点样式` —— `_chrome_html_check` 加 `has_header_landmark`/`has_main_landmark`/`has_section_landmark`/`has_footer_landmark`；`_chrome_css_check` 加 `has_focus_styles`/(`has_active_styles`)；recommendations 移除已落地项。
    - **历史路径说明**：6700c70 把"语义标签缺失"设为软告警（不阻塞门禁）+ recommendations 列入改进工单；本次 commit 链落地后回填硬门禁（见 `feedback_test_gate_design.md` 分层原则）。
    - **关键决策点**：用 `:focus-visible` 而非 `:focus`（避免鼠标点击的 outline 视觉干扰，仅键盘 tab 聚焦时显示，符合 WAI-ARIA 最佳实践）；`<section>` 用 `aria-labelledby` 关联 `<h3>`（比裸 `<section>` 对 screen reader 更友好）。
    - **验证**：tests/e2e/ 全套 47/47 通过；全量 2350 passed / 0 failed / 6 skipped（Python 3.14.6）；ruff 全绿。
    - **新增非阻塞工单**：`<li class='pack-item'>` 当前不可 tab 聚焦，未来若改为 button 或加 tabindex=0 + role 时，需同步补 `:focus-visible` 样式（已写入 recommendations）。

### 文档任务
- TASK-W11-D5-README-DOCUMENTATION-005: README 和部署文档（README.md 已存在，需校验任务收尾状态）
- TASK-20260228100945-004: 文档完整性检查（待校验）

### 代码清理
- **Backend Ruff 清零**: ✅ 已完成并提交（2026-09-19），按改动类别拆分为 3 个聚焦 commit：
  - `576b2a5` `chore(ruff)`: 扩展检查面，移除 local-backend 的 E/F 豁免（pyproject.toml）
  - `d6e5272` `chore(vscode)`: 解释器路径 anaconda3 → miniforge3
  - `a39a76a` `refactor(ruff)`: pyupgrade 现代化修复（110 文件）
  - 门禁验证：`ruff check ai_collab local-backend/app src` 全绿；工作区干净；`test_api.py` + `test_state_manager.py` 48 passed
  - 环境补齐：miniforge3 迁移后本机缺 ruff、fastapi，已 `pip install ruff` + `pip install -r local-backend/requirements.txt`
  - **后续独立待办**：`ruff format` 仍有 100 文件未格式化（32 已格式化）——原 acceptance 只要求 `check`（lint），format 属独立工作，尚未推进（非阻塞）

### 环境变更记录 (2026-09-19)
- **Python 环境迁移**: anaconda3 → miniforge3
  - 旧路径: `/Users/raymondna/anaconda3/bin/python` (已不存在)
  - 新路径: `/Users/raymondna/miniforge3/bin/python3`
  - Python 版本: 3.14.6
  - **已修复**: `.vscode/settings.json:47` 中 `python.defaultInterpreterPath` 旧路径引用 (2026-09-19)
  - **依赖补齐（2026-09-19）**: miniforge3 迁移后本机缺失以下依赖，全部已 `pip install` 补齐 —— aiohttp 3.14.3 / pyyaml / mypy 2.3.1 / pytest-cov 7.1.0 / pytest-asyncio 1.4.0 / pytest-timeout 2.4.0。补齐前测试 2315 collected + 3 errors，补齐后 2354 collected / 0 errors（基线：2327 passed / 22 failed / 6 skipped）

## 架构演进记录

### 精简重构（分支 `refactor/slimming-2026-09-20`，2026-09-20）
- **更新（2026-09-26 核实）**：`refactor/slimming-2026-09-20` 与 `main` **均已移除** `ReviewWorkflow` 组件（原记忆"main 仍保留它"已过期）；工作区（未提交改动）反而混入了**旧版本的 `ReviewWorkflow`**，与两个分支的 HEAD 都不一致。
- **Why**: 分支名表明这是精简（slimming）导向的重构；具体动因未在会话中记录。
- **How to apply**: 涉及 `ReviewWorkflow` 的改动前，先确认当前分支与工作区版本（`git status` / `git diff`），避免基于任何单一版本做出错误假设（旧记忆曾误判 main 仍保留）。

### 并行协作者与工作区污染（2026-09-26）
- 本仓库存在**活跃的并行协作者/进程**在同一工作区同时操作：`main` 会被其他进程推进，当前 HEAD 可能不在预期分支（曾停在 `refactor/slimming-2026-09-20`），工作区可能混入非本会话的未提交改动（数百行，来自其他协作者）；本会话产出的 commit 已在 `main` 上。
- **Why**: 2026-09-26 提交任务时核实状态发现，贸然提交会污染其他进程工作，贸然 `checkout`/`reset` 会丢失其他进程的未提交改动；本会话曾基于过期代码（`main` 旧版本，含已被删除的 `ReviewWorkflow`）准备改动，导致改动不可直接移植。
- **How to apply**: 任何 commit / 切换分支 / 清理工作区前，先 `git status` + `git log` 核实当前分支与工作区归属，区分「本会话改动」与「他人未提交改动」；禁止用 `checkout`/`reset --hard` 强清工作区；改动前先确认目标代码版本是否为最新。
- **用户定性（2026-09-26）**: 用户明确要把本次并行冲突当作**样本案例**，转化为 AI Collaboration System 在**治理层**和**服务层**的**可复用能力增强**，而非只做一次性修复。
  - **How to apply**: 后续涉及并行协作 / 冲突处理的需求，优先从"可沉淀为治理层（规则/协议/看板约束）与服务层（自动化冲突检测/交接机制）的通用机制"角度设计；先探索现有治理层与服务层架构现状再动手。

### 仓库边界：不得存放外部项目副本（2026-09-26 发现，2026-10-23 清理完毕）
- **硬规则**：本仓库根目录下**不得存放任何非本仓依赖的第三方/外部项目代码副本**。外部项目的东西要么放在它自己的机器/仓库里，要么以「本仓自带的等价实现」形式落地，绝不以来源不明的目录形式躺在仓里。
- **Why**: 2026-09-26 曾有一个外部项目的移植目标目录躺在仓里，导致 pytest 全量 collection error（`ModuleNotFoundError`），且被 pytest 从根目录收集、污染覆盖率分母 —— 那时它是「全量 pytest 的唯一阻断项」，排查成本远高于收益。更根本的问题是：外部项目的代码副本在本仓**无法被复跑验证**（依赖不在本仓），却会持续出现在工单、结果文件、文档里，把后续开发带偏。2026-10-23 已连同该外部项目的变更提案、任务契约、记忆条目一并清理。
- **How to apply**:
  1. 外部项目的移植/对接需求 → **在本仓落地等价能力**（如 Consensus Engine 本仓已有产品级实现 `ai_collab/engines/consensus_engine.py`），不保留来源代码副本；
  2. 确需引用外部产物 → 只保留**结果回执**（放 `collaboration/results/RESULT_*.md`）并明确标注「历史事实、路径已不存在、命令不可复跑」；
  3. `pyproject.toml` 的 `[tool.pytest.ini_options] testpaths = ["tests"]` 是白名单，**保留**（这是兜底防线，不是临时补丁）；若未来测试置于 tests/ 之外需同步更新 testpaths；
  4. 工单的 `acceptance_commands` 必须**指向本仓可复跑的命令**，不得指向已删除或不在本仓依赖内的路径。

## 质量基线快照（2026-10-22 现场核验，slimming 分支领先 main 20 提交）
- 全量测试: **2660 passed / 0 failed / 6 skipped**（36s，Python 3.14.6）
- 单元+覆盖率（对齐 CI 口径含 omit）: 2344 passed，**TOTAL 88%**（14581 stmts / 1698 missed）
- mypy: **0 错误**（99 源文件）；ruff: 全绿
- 2026-09-20 审计报告的「mypy 109 错误 / 覆盖率 81% / CI 无门禁」三项均已过期失效；CI 已有 7 个 workflow（test/fail-under=85/lint/mypy-gate/nightly/security/healthcheck）
- **How to apply**: 引用 2026-09-20 前的审计/分析报告数据前，先以本节基线校准。
- **2026-10-22 收尾后仍红的项**: 治理报告 stale（result-consistency 生成于 2026-09-19）、`_cli_main.py` 5,027 行未拆（并行任务 TASK-P1-GOV-CONVERGE-001 在途）、`pyproject.toml` testpaths 修复未入库（见上）。已转绿：分支推送、gen_facts 接 CI、CONFLICT-1772060801 残留清理、历史规则文件归档。全量测试最新基线 2686 passed / 6 skipped / 0 failed。

## 历史规则文件归档约定（2026-10-22 建立）
- 6 个历史 Agent 专属规则文件已移至 `rules/archive/`：`claude_code_memory.md`、`codex_agent_rules.md`、`codearts_agent_rules.md`、`copilot_rules.md`、`trae_rules.md`、`agent_governance_quickstart.md`，均带「已归档，不参与会话启动」警告头。
- `rules/` 根目录保留的活跃文件：`AI-COLLABORATION-STANDARDS.md`、`OWNERSHIP.md`、`OWNERSHIP_UPDATE.md`、`copilot_tasks.md`、`dev-record-template.md`。
- **Why**: 这些文件此前以「P2 历史参考」半死状态存在，文件还在、还在被引用，比删除更危险；且 `CLAUDE.md` 的 P0 必读清单曾把已归档的 `claude_code_memory.md` 列为强制必读，与 P2 定位自相矛盾。
- **How to apply**: 会话启动读规则时 `rules/archive/` 下内容仅作历史溯源，**不得作为当前角色绑定依据**；当前绑定见 `config/agent-orchestration.json`，必读清单见 `collaboration/AI_BEHAVIOR_CONSTRAINT_FILES.md`。

## 事实快照约定（2026-10-22 建立）
- `scripts/gen_facts.sh` 输出固定为 `docs/FACTS.generated.md`（唯一事实源，废弃时间戳文件名避免快照堆积）；已接入 `.github/workflows/nightly.yml` 生成 + artifact 上传（不自动提交回仓库，人工刷新保持单一责任人）。
- 脚本第 3 节远端同步基于当前分支 upstream（`@{u}`），不硬编码 `main`（2026-10-22 修正的 bug：原写法在非 main 分支上语义完全错误，会把 ahead 20 误报成 unpushed）。
- **How to apply**: 需要「项目事实」时优先读 `docs/FACTS.generated.md`，**不要写新的手写全貌文档**（手写文档复述事实必然漂移，项目已因此累积多代互相矛盾的文档口径）。

## 已完成项
- 任务工单闭环: 60/52 ✅
- Patch 闭环: 16/10 ✅
- 状态漂移修复: 3项 ✅
- USER_GUIDE 文档: 5个 ✅
