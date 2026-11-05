# AI Collab Base — 项目应用范例与交互过程详解（2026-11-05 修订版）

> **修订说明**：本文是《项目应用范例与交互过程详解》的修订版。原稿经两轮真机实测对账
> （`collaboration/results/RESULT-PACK-REALTEST-2026-11-05.md` 文件/命令面对账、
> `RESULT-RUNTIME-REALTEST-2026-11-05.md` 范例二~五运行时实测），凡与实盘不符处已改写；
> 关键更正以 **〔修订注〕** 标出。命令、URL、字段名均可照抄运行。
>
> 口径：**实测成立**（真机验证过）/ **代码层成立**（源码实证，未跑端到端）/ **规划态**（尚不存在，勿照抄）。

---

## 范例一：小红书美妆测评内容创作（单平台 Pack 工作流）

场景描述：美妆品牌运营人员需要为新品口红撰写小红书测评笔记。可加载的示例 Pack 是 **`xiaohongshu-beauty-review`**（小红书美妆测评文案生成包 v2.0.0）。

〔修订注〕原稿三处硬伤已改：① Pack 文件在 **`packs/templates/`**（2026-11-03 目录拆分自 examples/ 迁入），不在 `packs/examples/`；② pack_id 是**连字符** `xiaohongshu-beauty-review`；③ 该 Pack 是 **6 步工作流且全步无 `prompt_template`**，不是 3 步 prompt_injection 剧本——引擎支持分支/模板注入（见下），但这只 Pack 不用。

### 交互过程

```
┌─────────────────────────────────────────────────────────────┐
│  步骤 1: 加载 Pack                                          │
└─────────────────────────────────────────────────────────────┘
用户操作:
  - 打开 Chrome 扩展 Popup
  - 导入 packs/templates/xiaohongshu_beauty_review.json（IMPORT_PACKS 通道）

系统响应:
  - service-worker.js 处理 IMPORT_PACKS 消息，按 metadata.pack_id 注册 Pack
  - 〔修订注〕原稿的「PackStorageManager + 后端 GET /packs/... + 5 分钟 TTL」
    是已归档的旧架构（tests/_archive/ 时代）；现行加载是 IMPORT_PACKS 直导
  - Popup 显示 Pack 元数据: 名称、版本、步骤数、目标平台

┌─────────────────────────────────────────────────────────────┐
│  步骤 2: 平台检测与适配                                      │
└─────────────────────────────────────────────────────────────┘
系统操作:
  - content-script 检测当前标签页 URL，依次调用适配器 detect()
  - 匹配命中则选中对应 adapter（如 claude-adapter）；未命中则用户手动选择
  - adapter 提供 getChatInput / clickSend / typingIndicator / 抽取契约

┌─────────────────────────────────────────────────────────────┐
│  步骤 3: Pack 执行引擎启动                                   │
└─────────────────────────────────────────────────────────────┘
系统操作 (pack-executor.js):
  - PackExecutor.execute(pack, runtimeOverrides)
  - _validateRuntimeOverrides(): 白名单恰好 4 个 key——
      user_query / context_injection / platform_selection / model_preference
  - maxIterations = steps.length * 3（防死循环；6 步 Pack 上限 18）
  - 支持 step.branches 分支跳转（BranchEvaluator，condition_type 含 contains/equals/regex/阈值）

┌─────────────────────────────────────────────────────────────┐
│  步骤 4: 逐步执行 Workflow（xiaohongshu-beauty-review 实况）│
└─────────────────────────────────────────────────────────────┘
6 步流水线（全步无 prompt_template，走各步 type 的本地/模型语义）:
  step_1_input (local) → step_2_analysis (analysis) → step_3_generation (generation)
  → step_4_validation (validation) → step_5_fusion (fusion) → step_6_tracking (tracking)
  〔修订注〕原稿的「Step 1 prompt_injection 模板替换 → Step 2 branch(contains 测评)
  → Step 3 prompt_injection 优化」不存在于该 Pack；branch/模板注入是引擎能力，
  有 prompt_template 的可运行示例见 packs/examples/xiaohongshu_knowledge_creator.json

┌─────────────────────────────────────────────────────────────┐
│  步骤 5: 结果输出                                            │
└─────────────────────────────────────────────────────────────┘
  - ExecutionStatus 标记 COMPLETED，结果写 chrome.storage.local
  - 后端记录执行历史: POST /api/packs/{pack_id}/executions
      〔修订注〕真实前缀是 /api/packs（不是 /packs）；请求体 {pack_id, input_data,
      output_data, step_results, ...}，status 由服务端置 pending 起步
  - Popup 显示最终内容，提供复制/导出
```

### 涉及文件
- `chrome-extension/src/background/pack-executor.js` — 执行引擎（BranchEvaluator / 白名单 / maxIterations）
- `chrome-extension/src/platforms/claude-adapter.js` / `adapter-utils.js` — 平台适配与注入
- `packs/templates/xiaohongshu_beauty_review.json` — Pack 定义（6 步）
- `local-backend/app/api/packs.py` — Pack API（`/api/packs` 前缀）
- 〔修订注〕`chrome-extension/src/utils/backend-client.js` **不存在**；扩展接后端走 `notebooklm-packexecutor-bridge.js` 内 fetch

---

## 范例二：多平台 AI 共创 + 共识提取 + 风格注入（三阶段流水线）

场景描述：技术博主综合多 AI 观点撰写深度技术文章，并以「董宇辉风格」输出。

### 交互过程

```
┌─────────────────────────────────────────────────────────────┐
│  阶段 1: 多平台并发注入                                      │
└─────────────────────────────────────────────────────────────┘
  - Popup 选择多平台执行模式，勾选目标平台，输入 prompt 并发注入
  - multi-platform-executor.js: findPlatformTabs → Promise.allSettled 并发注入
  - 每 2 秒轮询 typing 状态直至全部完成（60s+ 超时策略以 wait-policy 为准，
    默认稳定窗 8 秒防思考停顿误判），收集各平台响应文本

┌─────────────────────────────────────────────────────────────┐
│  阶段 2: 后端共识提取                                        │
└─────────────────────────────────────────────────────────────┘
POST http://127.0.0.1:8000/api/consensus/generate
Body: { "topic": "Python 异步编程最佳实践" }
      〔修订注〕原稿的 {responses, strategy:"merge_best_points", min_confidence}
      三字段不存在（实测 422）；可选字段为 providers / timeout / real_responses
      （real_responses 是 Chrome 侧真实响应的混合模式入口）

后端处理 (app/api/consensus.py → engines/consensus_engine.py):
  - generate_consensus(topic): 按模式查询多 AI（MOCK/FALLBACK/REAL，生产默认 FALLBACK）
  - _extract_consensus: 合并各源响应文本（当前实现为按源拼接）
  - _verify_consensus: <50 字或含「错误/不确定」→ 返回风险提示
  - 返回 {topic, consensus, sources, timestamp, version, mode}
  - 幂等：同 topic 命中实例缓存（无锁，不保证并发只算一次）
  〔修订注〕原稿的「提取关键论点/去重合并/置信度 0.95/0.80/0.50 分级列表」
  不在本引擎；论点级去重与置信度计算在 multi_source 聚合器（范例四）

┌─────────────────────────────────────────────────────────────┐
│  阶段 3: 风格注入 (Soul Injection)                          │
└─────────────────────────────────────────────────────────────┘
POST http://127.0.0.1:8000/api/soul/inject
Body: { "consensus": "<共识文本>", "profile_name": "dongyuhui" }
      〔修订注〕原稿的 content/style_profile/viewpoint 字段名不对；
      viewpoint 无请求参数（内建于 profile）

后端处理 (app/api/soul.py → engines/soul_injection_engine.py):
  - SoulInjectionEngine.inject_soul: 策略链注入
      StyleInjectionStrategy → MethodInjectionStrategy → ViewpointInjectionStrategy
  - 内置 profile: luoyonghao（直率幽默）/ daojie（实用系统）/ dongyuhui
      dongyuhui 实值: style=诗意、温暖、有深度; method=故事化表达、情感共鸣;
      viewpoint=知识是光，照亮前行的路; keywords=[就像, 你会发现, 这让我想起, 在那一刻]
  - **幂等性**：同 (consensus, profile) 缓存键，重复注入结果逐字一致（实测成立）
  - 输出 {success, original_consensus, personalized_content, soul_profile,
        strategies_applied, timestamp, mode}
  〔修订注〕原稿的输出样例「朋友们，让我们聊聊…」不复现；真实注入形态是
  「就像{原文}…你会发现，这背后有更深的含义。【方法论】…【核心观点】…」——
  模板句式改写，不是 LLM 温润重写
```

### 涉及文件
- `chrome-extension/src/background/multi-platform-executor.js` — 多平台执行
- `local-backend/app/api/consensus.py` / `soul.py` — 共识/风格 API（前缀 `/api/consensus`、`/api/soul`）
- `ai_collab/engines/consensus_engine.py` / `soul_injection_engine.py` — 双引擎
- `local-backend/app/db/style_db.py` — 风格预设库（含 dongyuhui）

---

## 范例三：多 Agent 软件开发协作（ACK 协议全流程）

场景描述：AGENT_ARCH / AGENT_EXEC / AGENT_TEST 三角色协作实现「用户认证模块」。

〔修订注〕**核心映射更正**：权威角色表在 `config/agent-orchestration.json` 的
`command_prefixes`——**`A.RUN → AGENT_EXEC`（执行者）、`X.RUN → AGENT_ARCH`（架构师）、
`C.RUN → AGENT_TEST`（测试者）**。原稿把 A.RUN 与 X.RUN 写反了。

### 交互过程

```
┌─────────────────────────────────────────────────────────────┐
│  步骤 1: 角色与服务商                                        │
└─────────────────────────────────────────────────────────────┘
$ python3 -m ai_collab.cli orchestration detect   # 检测可用 AI 服务商
$ python3 -m ai_collab.cli orchestration status   # 绑定状态 + 角色 + 命令前缀
  〔修订注〕orchestration 子命令是 status/detect/roles/snapshot/history；
  原稿的 `orchestration cold-start` 不存在。detect 实测输出形如:
    claude_code: connected / codex_cli: unavailable / ...
  绑定态是 config/agent-orchestration.json 的 binding_status（实盘值 active）

┌─────────────────────────────────────────────────────────────┐
│  步骤 2: 派发与执行 (X.RUN → AGENT_ARCH 先行设计)            │
└─────────────────────────────────────────────────────────────┘
  - 任务派发写入 logs/collaboration_state.json（StateManager 权威状态）
    + dispatch/receipt/ack-bridge 各自的 items 状态机
  - AGENT_ARCH 产出 docs/auth-module-design.md

┌─────────────────────────────────────────────────────────────┐
│  步骤 3: 显式 ACK                                            │
└─────────────────────────────────────────────────────────────┘
  真实 ACK 行格式（build_ack_line）:
    {P}.ACK|task={task_id}|status={status}|result={result_file}
  例: X.ACK|task=TASK-AUTH-001|status=ok|result=docs/auth-module-design.md
  〔修订注〕原稿的「A.ACK TASK-xxx completed. 产出: …」不是系统格式；
  前缀 P 由角色/绑定 provider 派生（provider 兜底表: claude_code→C、
  codearts_agent→A、codex→O；role_prefix.py 收敛两套命名空间，字母池不重叠）
  〔修订注〕「解析 A.ACK 前缀」的说法不准——is_explicit_ack_source 校验的是
  ACK **渠道身份**（cli-ack / chat-ack），不是消息里的字母前缀
  补票命令: python3 -m ai_collab.cli ack --task-id <ID> --ai <provider> --status ok

┌─────────────────────────────────────────────────────────────┐
│  步骤 4: 看门狗 + 结果一致性审计（实测成立）                  │
└─────────────────────────────────────────────────────────────┘
  - ack_watchdog.run_ack_watchdog: 扫 dispatch/receipt/ack-bridge，
    揪出「超阈未 ACK」的静默任务（时间闸/终态/已 ACK 正确排除，实测成立）
  - result_consistency_audit.run_terminal_result_consistency_audit:
    终态任务 vs result_file 对账——有产物 consistent、缺产物 missing_result_file
    （默认产物路径 collaboration/results/RESULT_{task_id}.md，实测成立）
  〔修订注〕状态文件真名是 logs/collaboration_state.json（写错层级会得到假阴性）
```

### 涉及文件
- `ai_collab/role_prefix.py` — 命名空间收敛（A.RUN/X.RUN 权威映射）
- `ai_collab/ack_protocol.py` / `ack_watchdog.py` / `result_consistency_audit.py`
- `ai_collab/state_manager.py` — `logs/collaboration_state.json`
- `config/agent-orchestration.json` — command_prefixes / 绑定

---

## 范例四：NotebookLM 知识增强的深度研究工作流

场景描述：咨询顾问撰写「中国新能源汽车市场分析报告」，多源知识聚合后结构化输出。

### 交互过程

```
1) 场景检测: ai_collab/context/scenario.py（ScenarioDetector，按工作区文件打分推荐 Pack）
2) 知识查询: ai_collab/integrations/notebooklm.py
   - IntegrationMode: MOCK / FALLBACK（生产默认）/ REAL
   - connect() 做 MCP 健康检查；不可用时 FALLBACK 回退 Mock（实测成立）
     〔修订注〕REAL 通路需 notebooklm-mcp 在线，未配好前请以 fallback 行为为准
   - query_knowledge(topic, context?) → {query, response, sources, timestamp, mode}
     〔修订注〕mock 层返回固定假源（document1.pdf 等），原稿的 fragment_1/2/3
     真实片段是 REAL 通路的期望形态；`notebooklm_cache.py` 相似度缓存**不存在**
3) 多源聚合: ai_collab/integrations/multi_source.py（实测成立的管道）
   KnowledgeAggregator.aggregate(query):
     选相关源 → deduplicate（精确去重）→ cross_validate（跨源共现验证）→
     merge（[Source N: type] 标签拼接）→ calculate_confidence
   〔修订注〕原稿「重叠信息保留高置信来源」只在精确重复时生效；
   「950 万辆→0.95 / 预测→0.75」分级样例不是实际输出形态
4) 知识图谱: ai_collab/integrations/knowledge_graph.py（节点/关系/相似度）
5) 研究工作流: ai_collab/integrations/research_workflow.py（大纲→多平台生成→共识→风格）
6) 学习推荐: ai_collab/context/learning.py + recommender.py（行为模式→下次推荐）
```

### 涉及文件
- `ai_collab/integrations/notebooklm.py` / `multi_source.py` / `knowledge_graph.py` / `research_workflow.py`
- `ai_collab/context/scenario.py` / `learning.py` / `recommender.py`
- `ai_collab/config/integration_flags.py` — 模式开关（env 可覆盖）

---

## 范例五：Hook 系统的会话保护与自动注入

场景描述：Claude Code 会话的注入、预检、快照、退出检查。（四 hook 全部 stdin JSON 协议，实测成立）

### 交互过程（实测输出形态）

```
事件 1: SessionStart → hooks/session_inject.py
  输出 additionalContext JSON:
    active_tasks / completed_tasks / last_intent / intent_category /
    lead_agent / support_agents + status.md 全文嵌入
  〔修订注〕原稿的「冲突警告」在有冲突 fixture 时才出现；注入内容比原稿精简

事件 2: PreToolUse(spawn_agent) → hooks/spawn_agent_preflight.py
  预检输出 permissionDecision: "deny" + 原因（实测拦截成立）
  例: "parent_task_id is required for spawn_agent delegation"
  通过时放行；文档/目标文件冲突、只读域等均在预检面内

事件 3: PreCompact → hooks/pre_compact.py
  快照: .cc-claude-codex/snapshots/<ts>-status.md + <ts>-state.json（copy2）
  〔修订注〕原稿的「logs/snapshots/ + 文件哈希 a3b2c1…」不符——
  无哈希计算，目录在 .cc-claude-codex/snapshots/

事件 4: Stop → hooks/stop_check.py（实测拦截成立）
  有未完成 → exit 2 阻断，消息含:
    status.md 未完成项 / 活跃协作任务 / **显式 ACK 缺失清单** /
    补票命令 (python3 -m ai_collab.cli ack …) / 🛑 标记提示
  干净 → exit 0 放行
  〔修订注〕原稿「三选一：ACK / 标 blocked / force-exit」与真实输出不符——
  真实给的是 ack CLI 补票与 status.md 🛑 标记，无 force-exit 选项
```

### 涉及文件
- `ai_collab/hooks/session_inject.py` / `spawn_agent_preflight.py` / `pre_compact.py` / `stop_check.py`
- `ai_collab/workspace_guard.py` / `ack_protocol.py`

---

## 范例六：Pack 的版本管理与兼容性检查

场景描述：管理 Pack 的校验、评分、版本与兼容性。

〔修订注〕原稿的 `pack publish / pack install / pack upgrade` 三条 CLI 曾**不存在**
（实测 `invalid choice`）；**2026-11-05 已落地**（`ai_collab/cli/pack_market.py`），
实测成立，命令如下。依赖解析/影响面分析在模块层
（`ai_collab/pack/dependency.py`、`prompt_pack/compatibility.py`），CLI 面现覆盖
发布/安装/升级主链。

### 交互过程（实盘命令面）

```
$ python3 -m ai_collab.cli pack list                 # 市场 Pack 列表
$ python3 -m ai_collab.cli pack validate --path packs/templates/xiaohongshu_beauty_review.json
    # schema 校验（metadata 8 字段 / 质量权重和 / 步骤 ID 唯一），实测「验证通过」
$ python3 -m ai_collab.cli pack rate add --name xiaohongshu-beauty-review \
      --user <你> --rating 5 --title "标题" --content "评价"
$ python3 -m ai_collab.cli pack rate list --name xiaohongshu-beauty-review
    # 评分入库（.reviews/ 运行时目录，已 gitignore）+ 均分/分布
$ python3 -m ai_collab.cli pack check-compat --source 1.4.0 --target 2.0.0
    # SemVer 版本号比较（如 BACKWARDS_INCOMPATIBLE: 主版本号增加）
    〔修订注〕这是版本号比较，不是 pack-vs-pack 影响面分析
$ python3 -m ai_collab.cli pack version bump|history --name <pack>
$ python3 -m ai_collab.cli pack import|export|template|search|browse|trending|…

# ── 市场发布/安装/升级（2026-11-05 落地，实测成立）──
$ python3 -m ai_collab.cli pack publish --path packs/examples/<id>.json [--approve]
    # pack validate 同款判据 + SemVer 校验 → 入市场库（默认 PENDING，--approve 直批）
    # 市场表是 pack_id 主键单行：同 id 发更高版本 = 单行覆盖（保留下载/评分计数），非更高版本拒发
$ python3 -m ai_collab.cli pack install <id>[@<范围>]
    # 选版（范围如 ^1.0.0，部分版本 ^1.0 自动补零，* 通配可用）→ 依赖解析（安装顺序/冲突）
    # → 登记 packs/.packs-index.json（下载计数 +1）
    # 市场库不持久化 dependencies（表无该列）——依赖图从 packs/ 正文 JSON 补齐
$ python3 -m ai_collab.cli pack upgrade <id>
    # 对比本地索引已装版本与市场最新 → SemVer 主版本破坏性提示 + 已装依赖冲突扫描 → 更新索引
```

〔修订注〕语义边界（实测对账）：① 市场库是 **pack_id 单行最新版**模型，无版本历史表，
新版本覆盖旧版；② dependencies 只在正文 JSON 中，市场库存元数据；③ 发布闸门用
`pack validate` 同款轻量判据——`schema_validator.validate_pack` 是另一套更严口径
（要求 metric 内嵌 name，仓库正典 Pack 不满足），不作发布闸门。CompatibilityReport
影响包分析仍无 CLI 入口（模块层 `prompt_pack/compatibility.py`）。

### 涉及文件
- `ai_collab/cli/_cli_main.py` — pack 子命令面（list/show/activate/recommend/version/check-compat/search/browse/trending/rate/share/validate/template/export/import/publish/install/upgrade/convert）
- `ai_collab/cli/pack_market.py` — publish/install/upgrade 门面（2026-11-05 落地）
- `ai_collab/pack/market_api.py` / `market_store.py` / `dependency.py` / `version.py` / `schema_validator.py`
- `ai_collab/prompt_pack/compatibility.py` / `rating.py`

---

## 总结：六大范例 × 实测判档

| 范例 | 核心能力 | 实测判档 |
|---|---|---|
| 小红书测评 | 单平台 Pack 工作流 | 引擎能力成立；示例 Pack 形态以本文为准（6 步无模板） |
| 多平台共创 | 并发注入 → 共识 → 风格注入 | 幂等/策略链成立；共识=拼接合并，字段名以本文为准 |
| 多 Agent 开发 | ACK 闭环 | 看门狗/审计/补票成立；A.RUN↔X.RUN 以本文映射为准 |
| 深度研究 | NotebookLM + 多源聚合 | fallback 与跨源验证成立；REAL 已打通共识 provider（Ollama 真模型），NotebookLM REAL 仍待 MCP 接入 |
| Hook 保护 | 注入/预检/快照/退出检查 | 四 hook 全部真拦截真注入；快照无哈希 |
| Pack 管理 | 校验/评分/版本/兼容 | 校验/评分/版本比较成立；publish/install/upgrade 2026-11-05 落地实测成立 |

> 更正溯源：`RESULT-PACK-REALTEST-2026-11-05.md`（文件/命令面）、
> `RESULT-RUNTIME-REALTEST-2026-11-05.md`（运行时行为）、
> `RESULT-REALPATH-MARKET-CLI-2026-11-05.md`（REAL 通路 + 市场 CLI 落地）。
> 发现新漂移请开条目追加实测。
