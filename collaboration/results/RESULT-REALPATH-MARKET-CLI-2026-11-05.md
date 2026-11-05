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

### 1.4 codex_cli / codearts 服务商 —— 阻塞 ✗

- 两者都需要外部 CLI 二进制（`which codex` 等 PATH 探测），本机未安装。
- 结论：**外部依赖缺失，通路不可测**。role_prefix 回退映射（claude_code→C、
  codearts_agent→A、codex→O）源码层成立，运行时未验。

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
| NotebookLM REAL | **阻塞**（MCP 连接器/builtin 缺失） |
| codex_cli / codearts 运行时 | **阻塞**（外部 CLI 未安装） |
| pack publish / install / upgrade | **成立**（31 单测 + 端到端真机链路全绿） |
| 市场表版本模型 / 依赖持久化 / 校验口径 / 范围语法 | 4 项模块层真相对账（§2.3），CLI 层已适配或绕开，根治留后续 |

## 四、后续

1. 共识引擎：失败 provider 显式降级标记（禁用 `[X REAL]` 假填充命名；mode_used 诚实化）。
2. schema_validator 与 pack validate 口径统一（metric name-as-key vs name-field）。
3. dependency.py 范围语法对齐（`*` 通配 / 部分版本 / AND 空格），或全库统一到严格子集。
4. 市场表 dependencies 列 + 版本历史（若需要多版本共存）——涉及 schema 迁移，单开条目。
5. NotebookLM MCP / codex CLI 接入后补 REAL 复测。
