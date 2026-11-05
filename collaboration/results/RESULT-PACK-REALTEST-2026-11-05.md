# RESULT — Pack 真机实测 · 《项目应用范例与交互过程详解》文档对账 · 2026-11-05

- 对象：用户提供的范例文档《AI Collab Base — 项目应用范例与交互过程详解》（6 范例，2026-11-05）
- 方法：磁盘真值对账（逐文件/逐符号）+ 真机实测（`python3 -m ai_collab.cli pack *` 命令批 + local-backend 真起服 API 批）
- 判档口径：**成立**（声明与实盘一致）/ **部分成立**（内核真、表述漂移）/ **不成立**（声明在实盘无对应物）
- 环境：macOS，conda python（miniforge3，backend 依赖在彼处），沙箱文件代理注记见 §5

## 0. 总判

| 范例 | 主题 | 判档 | 一句话 |
|---|---|---|---|
| 范例一 | 小红书美妆测评单平台 Pack 工作流 | **部分成立（大漂移）** | 引擎能力声明基本真，但 Pack 文件路径/加载架构/步数步骤型全错——纸面流程跑不通 |
| 范例二 | 多平台共创 + 共识 + 风格注入 | 文件真值成立（未实测运行） | 涉及文件 8/8 存在 |
| 范例三 | 多 Agent ACK 协议 | 文件真值成立（未实测运行） | 涉及文件 8/8 存在 |
| 范例四 | NotebookLM 深度研究 | 文件真值成立（未实测运行） | 涉及文件 8/8 存在 |
| 范例五 | Hook 会话保护 | 文件真值成立（未实测运行） | 涉及文件 5/5 存在 |
| 范例六 | Pack 市场版本管理 | **部分成立（命令面大漂移）** | 模块全真，但 publish/install/upgrade 三条 CLI 命令不存在，rate 语法不符 |

## 1. 范例一实测（Pack 加载/执行链路）

| # | 文档声明 | 实测真值 | 判档 |
|---|---|---|---|
| 1 | `packs/examples/xiaohongshu_beauty_review.json` | 2026-11-03 目录拆分后移居 **`packs/templates/`**（`tests/e2e/test_integration.py` 注释实锤），examples/ 只剩 README + external-user-smoke + knowledge_creator | **不成立**（路径过时） |
| 2 | `PackStorageManager` 读 chrome.storage，miss 时 `GET http://127.0.0.1:8000/packs/...`，5 分钟 TTL | `PackStorageManager` 只存 `tests/_archive/p2-pack-storage-test.js`（还指着老项目路径 `ai-collab-system/`），**生产代码已无**；现行加载是 `IMPORT_PACKS` 消息直导（service-worker.js:307）；且扩展内**任何** `/packs/` fetch 都不存在 | **不成立**（旧架构遗音） |
| 3 | 「5 分钟 TTL」 | 代码真值：`PACK_CACHE_TTL_SECONDS=120`（2 分钟）、`METADATA_CACHE_TTL_SECONDS=300`（5 分钟）——5 分钟只对 metadata 缓存成立，且是**后端**缓存不是扩展缓存 | **部分成立** |
| 4 | Pack 是 3 步工作流：`prompt_injection → branch(contains "测评") → prompt_injection` | 真实 pack **6 步**：`local → analysis → generation → validation → fusion → tracking`，全 6 步**无 prompt_template**（`tests/e2e` 注释：「无 prompt_template…不要求 Pack 可运行」），全仓 pack 内**无 branch/prompt_injection/user_query/context_injection 字样** | **不成立**（步骤形态整体虚构） |
| 5 | runtime_overrides 白名单 4 key（user_query/context_injection） | `ALLOWED_OVERRIDE_KEYS = ["user_query","context_injection","platform_selection","model_preference"]`（pack-executor.js:14）——恰好 4 个且含文档所举 2 个 | **成立** |
| 6 | `BranchEvaluator.evaluate()`，条件 contains | pack-executor.js:175 `class BranchEvaluator`，condition_type 含 `contains`（`String(targetValue).includes(...)`）——引擎支持分支，只是 beauty pack 不用 | **成立**（引擎层） |
| 7 | `maxIterations = steps.length * 3 = 9 (3 步骤)` | 公式一字不差（pack-executor.js:473 `const maxIterations = steps.length * 3`）；但「3 步骤」错——该 pack 6 步 ⇒ 上限 18 | **部分成立** |
| 8 | `claude-adapter.getChatInput / clickSend`、`adapter-utils.injectTextSmart`、`waitForResponse` 60s | 文件全在（claude-adapter.js / adapter-utils.js / wait-policy 链）；本轮未走 Claude 实链（L2 实链在 qianwen 上有 2026-11-05 两轮真机证据） | **成立**（代码层） |
| 9 | `chrome-extension/src/utils/backend-client.js` | **全仓无此文件**；扩展接后端实际走 `notebooklm-packexecutor-bridge.js` 内 `fetch(backendUrl)` | **不成立** |
| 10 | 后端 `GET /packs/{id}` 吐元数据 | 真实路由前缀是 **`/api/packs`**（main.py:203）；且 DB 冷启动为空，文档原断言 `GET /packs/xiaohongshu_beauty_review` **三重 404**（前缀错 + id 分隔符错 + 未入库） | **不成立**（URL 不可照抄） |
| 11 | 后端 `POST /packs/{id}/executions` 记录执行历史 | 路由真实（packs.py:530，`POST /api/packs/{id}/executions`）；实测 **201** 建档 + 列表可查。但 schema 是 `input_data/output_data/step_results`、status 强制 `pending`——不是自由「记录执行历史」 | **部分成立** |

**范例一补一条 id 实锤**：beauty pack 内部 `metadata.pack_id = "xiaohongshu-beauty-review"`（**连字符**），文档通篇写 `xiaohongshu_beauty_review`（下划线）——即使包已入库，文档 URL 仍 404。实测：POST 原文入库 → `GET /api/packs/xiaohongshu-beauty-review` 200 全量元数据。

**真机启动链发现（文档未提，实测撞上）**：
1. local-backend 从 `local-backend/` 起必须 `PYTHONPATH=<仓库根>`——`packs.py` import `ai_collab.pack.schema_validator`，否则 `ModuleNotFoundError: ai_collab`。
2. 本机 8000 端口被**另一服务**占用（`/health` 自报 neo4j/milvus/8 agents registered 的 agent 平台），不是 prompt-pack-api——文档「127.0.0.1:8000」在本机不成立，实测改用 **18000**，起服后 `/health` 自报 `service: "prompt-pack-api"`（与 known_gaps.json 身份判据一致）。

## 2. 范例六实测（Pack 市场 CLI）

命令批真跑（错误原文已取证）：

| # | 文档命令 | 实测结果 | 判档 |
|---|---|---|---|
| 1 | `pack publish ecommerce-content.json` | `error: invalid choice: 'publish'`（真实子命令：list/show/activate/recommend/version/check-compat/search/browse/trending/rate/share/validate/template/export/import/convert） | **不成立** |
| 2 | `pack install ecommerce-content-generator@2.0.0` | `error: invalid choice: 'install'` | **不成立** |
| 3 | `pack upgrade generic-writing-framework` | `error: invalid choice: 'upgrade'` | **不成立** |
| 4 | `pack rate <name> --stars 5 --review "..."` | `error: invalid choice: 'ecommerce-content-generator'`——真实是 `pack rate add --name X --user Y --rating N --title T [--content C]`（子命令 add/list，参数名全不同） | **不成立**（语法） |
| 5 | 评分系统本身 | `pack rate add` 5★ **实测成功**（写 `.reviews/`），`rate list` 出「1 条 / 均分 5.0★ / 分布」 | **成立** |
| 6 | Schema 验证（ValidationIssue 0 errors） | `pack validate --path packs/templates/xiaohongshu_beauty_review.json` **实测「验证通过」**（metadata 8 字段全 ✓、质量权重和 1.000、6 步 ID 唯一） | **成立** |
| 7 | 兼容性检查（CompatibilityReport，影响包分析） | `pack check-compat --source 1.4.0 --target 2.0.0` 实测是**两版本号 SemVer 比较**（输出 `BACKWARDS_INCOMPATIBLE：主版本号增加`），无「影响包/影响程度」分析 | **部分成立** |
| 8 | `pack list` 市场列表 | 实测出 4 个 market pack（api-design-pack/demo-pack/python-best-practices/web-dev-pack）；templates/ 与 examples/ 的 pack **不在**市场列表 | **成立**（附注记） |
| 9 | 模块面：market_api/dependency/version/schema_validator/compatibility/rating | 6/6 文件存在（另有 `ai_collab/cli/pack_dependency.py` 解析器，无 CLI install 入口） | **成立**（模块层） |

## 3. 范例二~五文件真值（未跑运行时实测）

逐条 `ls` 对账，**28/28 存在**：consensus.py / soul.py / consensus_engine.py / soul_injection_engine.py / style_db.py / agent_orchestrator.py / ack_protocol.py / ack_watchdog.py / result_consistency_audit.py / spawn_agent_guard.py / workspace_guard.py / state_manager.py / daily_report.py / config/agent-orchestration.json / scenario.py / notebooklm.py / multi_source.py / knowledge_graph.py / research_workflow.py / learning.py / recommender.py / integration_flags.py / hooks×3 / market_api.py / market_store.py / dependency.py / version.py。全仓唯一缺失文件是范例一的 `backend-client.js`（§1 #9）。

——此四例的**运行时**行为（共识质量、ACK 闭环、NotebookLM 检索、Hook 拦截）本轮未实测，声明保留在「文件真值成立、行为待测」档，不做行为背书。

## 4. 与文档的结构性差异（一句话诊断）

文档把**引擎能力**（branch/白名单/maxIterations）、**旧架构遗音**（PackStorageManager/Backend Client/TTL）、**虚构步骤形态**（3 步 prompt_injection 剧本）缝合在 beauty pack 名下；而实盘的 beauty pack 是另一只动物（6 步无模板、templates/ 目录、连字符 id）。**照抄文档 URL 与命令跑不通，照抄引擎概念可以。**

## 5. 环境注记（防误判）

1. `pack rate list` 首跑崩 `FileExistsError: mkdir '.reviews'`——**环境假阳性**：repo 代码是 `mkdir(exist_ok=True)`（rating.py:99），WorkBuddy 沙箱文件代理（sitecustomize shim）丢 `exist_ok` 所致；`python3 -S` 绕开代理复跑正常。非 repo bug。
2. backend 实测用 18000 端口（8000 被无关服务占用）与 `PYTHONPATH` 均为本机环境适配，不改 repo。
3. `.reviews/` 为 `pack rate` 运行时数据，已随本 PR 补入 `.gitignore`。

## 6. 建议（锉一刀，不替文档作者改稿）

1. 文档若要留：范例一的步骤剧本应换成 beauty pack 真形态（6 步）或改用 knowledge_creator（有 prompt_template 的真 3 步链），并全局改 `packs/templates/` 路径与 `xiaohongshu-beauty-review` 连字符 id。
2. 范例六命令面换成真实子命令（`rate add`/`check-compat --source --target`/`import`/`export`），或注明 publish/install/upgrade 为规划态。
3. `PACK_CACHE_TTL` 有 env 开关（`PACK_CACHE_TTL_SECONDS` 等），文档引数值时应带「默认」二字。
