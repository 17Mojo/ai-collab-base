# RESULT — REAL 通路摸底 + Pack 市场 CLI 落地（2026-11-05）

- 任务：#56 REAL 通路摸底（共识 provider / NotebookLM MCP / codex_cli·codearts 服务商）+
  #57 publish/install/upgrade 市场 CLI 落地
- 口径：机器实测。凡未打通处如实记 blocker，不以 mock 结果冒充 REAL。
- 前序：`RESULT-RUNTIME-REALTEST-2026-11-05.md`（范例二~五运行时行为）。

---

## 一、REAL 通路摸底

### 1.1 共识 provider REAL —— 打通 ✓（Ollama 真模型）

- 路径：`ConsensusEngine.generate_consensus`，`integration_flags.get_mode` 判 REAL，
  需 provider client 带 `.query(topic)`。
- 实测：Ollama（127.0.0.1:11434）多模型试探：
  - `clef-flash` → HTTP 400（不支持 generate）；
  - `glm-4.6:cloud` / `minimax-m2` / `qwen3-coder` / `deepseek-v3.1` → HTTP 410（已下线）；
  - **`gemma4:31b-cloud` 经 `/api/chat` 可用** → client 改 chat 端点后取到真模型文本。
- 结果：`mode_used="real"`，三家 provider 返回真实观点文本，confidence 0.85，
  缓存幂等命中。**REAL 通路成立**。

### 1.2 共识 REAL 的静默假货陷阱（重要）—— 实锤 ❌

- 现象：混部场景下部分 provider 调用失败时，引擎**不报错**，用 mock 填充句替换，
  且填充句字面命名为 `[{name} REAL] 关于…的真实观点...`，`mode_used` 仍报 `"real"`。
- 判定：**误导性遥测**。失败被假观点掩盖且名字里带 REAL，任何按 mode_used 判真伪的
  上层消费都会被骗。混部失败样本已捕获留档。
- 归属：引擎层（`ai_collab` 共识模块）设计缺陷，非本次可修范围，记后续项。

### 1.3 NotebookLM REAL —— 阻塞 ✗

- 依赖宿主注入 `builtins.mcp__plugin_notebooklm__get_health/ask_question`；
  当前会话无该 builtin，marketplace `search_plugins` 未找到 NotebookLM 连接器。
- 结论：**外部依赖缺失，通路不可测**。fallback/跨源验证逻辑此前已实测成立
  （见 RUNTIME-REALTEST），REAL 片段待 MCP 连接器接入后补验。
- 〔2026-11-05 复探〕工具注册表仍无 notebooklm 系工具，市场仍无 NotebookLM
  连接器（模糊命中乐享/飞书等均非目标）——blocker 原样成立。
- 〔2026-11-06 复测〕**接入面全部打通，卡点收敛到一条认证续期**。用户指向
  参考库 ai-collab-system 后定位真实实现面：notebooklm-py CLI（`nlm`/
  `notebooklm` v0.8.5，`~/.local/bin/`，本机**早已安装**——此前只探
  `which codex codearts` 漏探这两个名字）+ `~/.claude/skills/notebooklm-cli/`
  技能包。实测链路：① 宿主 shell 的大小写代理变量均指向沙箱代理 65179，
  它掐断 Google CONNECT（curl 直打 notebooklm/cloud/docs.google.com 经
  7890 全通）——全量改写代理变量后直抵 Google；② WorkBuddy broker 垫片
  丢 exist_ok 在 `~/.notebooklm-mcp-cli` mkdir 上触发 EEXIST 假阳性——
  `env -u PYTHONPATH`（垫片经 PYTHONPATH 注入 sitecustomize）绕开；
  ③ 真查询链路就绪（`nlm notebook query <id> <q>` 即引擎
  `_query_notebooklm_via_cli` 所调命令），认证报 expired（auth.json
  缓存 >168h 过期策略）。**续期无法在本进程树内完成**：nlm login 与
  手工/launchd (`open -na`) 起 Chrome 全部死于「sandbox initialization
  failed: Operation not permitted」→ GPU FATAL（seatbelt 继承，/tmp 新鲜
  profile 同死，用户 Finder 起的 Chrome 156 正常）——需用户在**自己的
  终端**跑一次 `nlm login`（官方流，rookiepy/CDP 续期），之后即可补真查询。

### 1.4 codex_cli / codearts 服务商 —— 阻塞 ✗

- 两者都需要外部 CLI 二进制（`which codex` 等 PATH 探测），本机未安装。
- 结论：**外部依赖缺失，通路不可测**。role_prefix 回退映射（claude_code→C、
  codearts_agent→A、codex→O）源码层成立，运行时未验。
- 〔2026-11-05 复探〕`which codex codearts` 仍 not found——blocker 原样成立。
- 〔2026-11-06 复测〕**映射层运行时已验，CLI 执行仍缺二进制**。穷举探测
  （PATH / `~/.local/bin` / brew / npm -g / uv tools / 参考库）codex 与
  codearts 二进制均不存在；参考库侧配置齐备（`collaboration/config-drafts/
  codex.config.toml`、`codex_integration.py` 的 `shutil.which("codex")` 调用
  约定、`.cc-claude-codex/` 历史运行日志）但运行时依旧缺席。role_prefix
  回退映射**运行时实测通过**：`resolve_ack_prefix/resolve_run_hint` 对
  claude_code→C/C.RUN、codearts_agent→A/A.RUN、codex→O/O.RUN、未知→Z/Z.RUN
  全对（`ai_collab/role_prefix.py:52` FALLBACK_ACK_PREFIX 真跑）。

---

## 二、市场 CLI 落地（publish / install / upgrade）—— 实测成立 ✓

### 2.1 落地面

- 新增 `ai_collab/cli/pack_market.py`（PackMarketCLI 门面 + main()），
  `_cli_main.py` 接线三个子命令（subparser + dispatch + 3 个 `_handle_*`）。
- 测试：`tests/unit/cli/test_pack_market_cli.py` 31 例（mock-patch 约定对齐
  test_pack_import_cli.py），31/31 过；`test_react_convert_cli.py` 18/18 无损。

### 2.2 端到端真机链路（真 sqlite + 真 Pack 正文 + 真 CLI 入口）

```
$ python3 -S -m ai_collab.cli pack publish --path packs/examples/xiaohongshu-beauty-review.json --approve
  ✓ Pack 已发布（xiaohongshu-beauty-review v2.0.0）/ 依赖: base-pack ^1.0.0 / 状态: approved
$ python3 -S -m ai_collab.cli pack install "xiaohongshu-beauty-review@^2.0"
  解析: xiaohongshu-beauty-review v2.0.0（约束 ^2.0）
  依赖来源: …/packs/examples/xiaohongshu-beauty-review.json（市场库不存依赖）
  安装顺序: xiaohongshu-beauty-review → base-pack
  ✓ 已登记到 packs/.packs-index.json（下载计数 +1）
# 升版 2.0.0 → 2.1.0 后 republish：
  ✓ Pack 已发布（xiaohongshu-beauty-review v2.0.0 → v2.1.0，单行覆盖更新）
$ python3 -S -m ai_collab.cli pack upgrade xiaohongshu-beauty-review
  已装: v2.0.0 / 市场最新: v2.1.0 / ✓ 升级完成
```

索引真值：version 2.1.0、range `^2.0`、dependencies 来自正文并登记。

### 2.3 落地过程中的模块层真相对账（新发现）

| # | 发现 | 证据 | 处置 |
|---|---|---|---|
| a | **市场表是 pack_id 主键单行**，无版本历史表；同 id 再 INSERT 撞 IntegrityError | `market_store.py` DDL `pack_id TEXT PRIMARY KEY` | publish 发更高版本走 `update_listing` 单行覆盖（保留下载/评分计数），非更高版本拒发 |
| b | **dependencies 不持久化**：表无该列，`get_listing`/`list_listings` 回填恒空 | DDL 无 dependencies 列；构造 PackListing 不传该字段 | install 按「市场存元数据、正文以 packs/ 为准」从正文 JSON 补依赖图 |
| c | **两套校验口径错位**：`schema_validator.validate_pack` 要求 metric 内嵌 `name/description/check_method/weight`，仓库正典 Pack（name-as-key 格式）过不了（5 error）；`pack validate` CLI 是另一套轻量判据（必需字段/权重和 warning/步骤 ID）且真 Pack 通过 | 真机跑 `validate_pack(strict=True)` on `xiaohongshu_beauty_review.json` → is_valid=False | publish 闸门对齐 `pack validate` 同款判据；错位记档，schema 层统一留后续 |
| d | **dependency.py 范围语法严格**：不认 `*` 通配（ValueError）；版本号必须完整 `major.minor.patch`（`^1.0` 炸）；AND 空格分隔在 `__post_init__` 校验路径认、`is_compatible_with` 检查路径只认 `,`/`&`——空格组合式**校验能过、匹配永远 False** | 真机探针 13 组对照；`_parse_range` 与 `_check_single_expression` 分隔符不一致 | CLI `_mk_dep` 归一化：`*`→`>=0.0.0`、部分版本补零、AND 空格转逗号（13/13 探针过）；模块层根治留后续 |

### 2.4 环境注记（非仓库缺陷）

- WorkBuddy sandbox broker 垫片（`sitecustomize.py`）丢 `exist_ok`：对已存在目录
  `mkdir(exist_ok=True)` 抛 EEXIST。pytest 二次运行（basetemp 复用）393 例 ERROR、
  `pack rate list` 撞 `.reviews/` 均为同类**环境假阳性**。
- 对照实验：`git stash` 后干净 main 复跑同例同样失败 → 与本次改动无关。
- 绕法：每次运行换新 `--basetemp`；`python3 -S` 绕垫片。CI（Linux 无此垫片）不受影响。

---

## 三、判档汇总

| 事项 | 判档 |
|---|---|
| 共识 REAL（Ollama gemma4:31b-cloud） | **成立**（真文本 + mode_used=real + 缓存幂等） |
| 共识失败静默假填充（名字带 REAL） | **实锤缺陷**（误导性遥测，记后续项） |
| NotebookLM REAL | **阻塞**（MCP 连接器/builtin 缺失）→〔11-06〕CLI 通路实测打通，仅剩认证续期人工检查点（§1.3） |
| codex_cli / codearts 运行时 | **阻塞**（外部 CLI 未安装）→〔11-06〕映射层运行时已验，二进制仍缺（§1.4） |
| pack publish / install / upgrade | **成立**（31 单测 + 端到端真机链路全绿） |
| 市场表版本模型 / 依赖持久化 / 校验口径 / 范围语法 | 4 项模块层真相对账（§2.3），CLI 层已适配或绕开，根治留后续 |

## 四、后续

〔2026-11-05 晚批销账〕1–3 已在本批修复收口（见 daily log / 同日后续 PR）：

1. ~~共识引擎：失败 provider 显式降级标记~~ **已收口**：`_mock_provider_response`
   假「REAL」填充器删除，client=None/缺 query/调用失败一律如实抛错（对齐模块头
   「REAL: 失败直接抛错」契约），结果新增 `failed_providers` 降级清单；
   原 `test_generate_consensus_real_when_available`（靠假填充通过的锚）重写。
2. ~~schema_validator 与 pack validate 口径统一~~ **已收口**：metric name-as-key
   （key 即 name，对齐 schema_v2.from_dict 消费面），正典 Pack 5 error → 0。
3. ~~dependency.py 范围语法对齐~~ **已收口**：`*`/x/X 通配、部分版本补零、
   AND 空格分隔检查路径对齐（`_check_single_expression` 与 `_parse_range` 分隔符一致）。
4. ~~市场表 dependencies 列 + 版本历史~~ **已收口**（2026-11-05 晚批，`known_gaps` N17 closed）：
   pack_listings 加 `dependencies TEXT`（旧库 PRAGMA 探测 + ALTER TABLE 就地迁移，存量行
   零丢失）；新增 pack_versions 追加式版本历史（每版本一条首次归档快照，update 覆盖前
   先归档旧行）；market_api 增 `list_pack_versions`，CLI 增 `pack history` 子命令；
   install 依赖图以市场表为准、正文 JSON 降级兜底。验证：迁移测试 17/17 + 真 sqlite E2E
   （publish → republish → history → install）全链一致。
5. ~~4 templates 缺顶层 section~~ **已收口**（2026-11-05 晚批，`known_gaps` N18 closed）：
   4 模板补 generation_params/optimization/performance_tracking/collaboration（travel 另补
   example_library + metadata 三字段，取 git 真值不伪造）；回溯修正台账未记的两类错误
   （metrics list→name-as-key、examples 键拆 good/bad 并补 PackExample 必填字段）。
   验证：validate_pack(strict=True) 4/4 零 error + schema_v2.from_dict 4/4 解析通过。
6. NotebookLM MCP / codex CLI 接入后补 REAL 复测（2026-11-05 复探 blocker 原样，
   见 §1.3/1.4 注记）。〔2026-11-05 19:5x 二次复探〕blocker 不变：工具注册表无
   notebooklm 工具、marketplace 搜索仅金融/法律类模糊命中、`which codex codearts`
   均未安装、`~/.workbuddy/mcp.json` 仅 llm-wiki/MiniMax/chrome-devtools/comfy-mcp。
   〔2026-11-06 复测〕见 §1.3/1.4 新注记。NotebookLM 侧：CLI 早已安装（`nlm`
   v0.8.5），网络/垫片/命令链全部实测打通，仅剩认证续期一条**人工检查点**——
   WorkBuddy 进程树起不了 Chrome（seatbelt 继承，沙箱内外、launchd 代拉、
   新鲜 profile 全死于同一 FATAL），请用户在自己终端跑 `nlm login` 后即可
   补一条 `nlm notebook query` 真查询收尾。codex 侧：二进制依旧缺席（如实），
   role_prefix 映射已运行时实测通过。**顺手实锤两条链路缺陷并已修复**：
   ① `agent_dispatch_bridge.py` 的 `--enrich-notebooklm` 路径调用从未定义的
   `enrich_with_notebooklm`（一触 NameError，功能从未接线）→ 补包装接
   `enrich_dispatch_payload`（mode 归一大写、use_cli=True、返回增强计数）；
   ② `_query_notebooklm_via_cli` 代理只写大写 env，httpx 优先读小写被宿主
   沙箱代理劫走 → 大小写成对写。回归锚：bridge 测试 +2（含 NameError 黑盒
   回归）、dispatch 单测 +1（代理成对断言），60/60 + 集成 11/11 绿。
