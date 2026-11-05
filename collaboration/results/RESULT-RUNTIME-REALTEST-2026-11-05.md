# RESULT — 运行时真机实测 · 范例二~五（共识/ACK/NotebookLM/Hook）· 2026-11-05

- 对象：《项目应用范例与交互过程详解》范例二~五的**运行时行为声明**（承接 `RESULT-PACK-REALTEST-2026-11-05.md` 的文件真值对账）
- 方法：引擎/模块层真跑（conda python + scratch workspace + stdin hook JSON）+ CLI/状态机实测；全部取证可复现（harness 见本节末）
- 判档：**成立 / 部分成立 / 不成立**；REAL 通路无凭据处如实标注「未验证」

## 0. 总判

| 范例 | 主题 | 判档 | 一句话 |
|---|---|---|---|
| 范例二 | 共识提取 + 风格注入 | **部分成立** | 幂等与策略链真；共识算法是拼接非提炼，API 字段与文档全不同 |
| 范例三 | ACK 协议闭环 | **部分成立（映射反转）** | 看门狗/审计真闭环；A.RUN↔X.RUN 文档写反，ACK 是渠道校验非前缀解析 |
| 范例四 | NotebookLM 检索 + 聚合 | **部分成立** | fallback 链与跨源验证真；mock 片段/相似度缓存不存在，REAL 未验证 |
| 范例五 | Hook 会话保护 | **大部分成立** | 四 hook 全部真拦截/真注入；快照无哈希、文案与选项有出入 |

## 1. 范例二实测（共识 + 风格注入）

### 1.1 ConsensusEngine（引擎层，fallback 实测）

| 声明 | 实测 | 判档 |
|---|---|---|
| 输入 `responses: [3 份文本]`, `strategy`, `min_confidence` | `generate_consensus(topic: str)`——主题词入口，内部多 AI 查询；API schema 为 `{topic, providers?, timeout?, real_responses?}`，文档三字段**全部不存在**（doc body 实测 422 `missing topic`） | **不成立** |
| 「提取关键论点→去重合并→置信度评分(3 源→0.95)」 | `_extract_consensus = "\n\n".join(response["response"] ...)`——**字符串拼接**；输出无「置信度」条目列表（实测 False）；sources 固定 mock 置信度 [0.9, 0.85, 0.88] 非计算值 | **不成立**（算法层） |
| 输出共识文档 | 输出 `{topic, consensus, sources, timestamp, version, mode}` 六键 ✓，但 consensus 是三段 mock 文拼接（"[ChatGPT Mock]…\n\n[Claude Mock]…"） | **部分成立** |
| 置信度门槛 min_confidence 过滤 | 无此机制 | **不成立** |
| （文档未提）验证闸 | `_verify_consensus` 真跑：含「不确定」→ 返回「共识内容存在不确定性，需要进一步验证」✓；<50 字 → 「共识内容不足」 | 成立（文档漏项） |
| （文档未提）缓存幂等 | 同 topic 二次调用命中 `self.cache`（timestamp 同）✓；并发契约有注释固化（无锁，不保证只算一次） | 成立（文档漏项） |

### 1.2 SoulInjectionEngine（引擎层，fallback 实测）

| 声明 | 实测 | 判档 |
|---|---|---|
| `POST /soul/inject`，body `{content, style_profile, viewpoint}` | 真实路由 **`/api/soul/inject`**；schema `{consensus, profile_name, timeout}`——`content→consensus`、`style_profile→profile_name` 改名，**`viewpoint` 参数不存在**（引擎层 TypeError 实证；doc body 422 `missing consensus`） | **不成立**（字段面） |
| `SoulProfile("dongyuhui"): 语气温润/句式长句/词汇文学化` | 真实 profile 字段是 `style="诗意、温暖、有深度", method="故事化表达、情感共鸣", viewpoint="知识是光，照亮前行的路", keywords=["就像","你会发现","这让我想起","在那一刻"]`——语义相近但字段结构与值不同；「技术应该有温度」不在任何 profile | **部分成立** |
| 模板系统风格转换 →「朋友们，让我们聊聊…」 | 真实是**策略链**（StyleInjectionStrategy→MethodInjectionStrategy→ViewpointInjectionStrategy，3 个策略实测全应用）；输出形态「就像{原文}\n\n你会发现，这背后有更深的含义。\n\n【方法论】…\n\n【核心观点】知识是光，照亮前行的路」——「朋友们」**不复现**（实测 False） | **部分成立**（机制真、样例虚构） |
| 幂等性检查：多次注入结果一致 | **成立**——同输入两次 `personalized_content` 逐字相同（cache_key 幂等） | **成立** |
| 观点注入「技术应该有温度」 | viewpoint 是 profile 内建字段（输出追加「【核心观点】知识是光…」），无请求级观点注入 | **不成立** |

## 2. 范例三实测（ACK 闭环）

### 2.1 命令与角色映射（文档核心反转）

| 声明 | 实测 | 判档 |
|---|---|---|
| `A.RUN → AGENT_ARCH(架构师)`，`X.RUN → AGENT_EXEC(执行者)` | **写反了**。`config/agent-orchestration.json` 权威表：`{"A.RUN": "AGENT_EXEC", "X.RUN": "AGENT_ARCH", "C.RUN": "AGENT_TEST"}`（`orchestration status` 输出同款）；`role_prefix.py` 文档化了两套命名空间收敛史 | **不成立**（映射反转） |
| `python3 -m ai_collab.cli orchestration cold-start` 交互式绑定 | `cold-start` 子命令**不存在**（真实：status/detect/roles/snapshot/history） | **不成立** |
| 「检测到 3 个可用 AI 服务商（claude/codex/codearts 全 ✓）」 | `orchestration detect` 实测：claude_code **connected**；codex_cli/gemini_cli/codearts_agent **unavailable**（1/4 可用） | **不成立**（本机） |
| `binding_status: uninitialized → bound` | 实盘 `binding_status: active`，绑定 AGENT_EXEC→codearts_agent、AGENT_ARCH→claude_code(sonnet)、AGENT_TEST→claude_code(sonnet) | **部分成立**（状态词与绑定值均不同） |

### 2.2 ACK 行与验证

| 声明 | 实测 | 判档 |
|---|---|---|
| ACK 格式 `"A.ACK TASK-AUTH-001 completed. 产出: docs/…"` | 真实 `build_ack_line` 输出**管道格式**：`{P}.ACK|task={id}|status={st}|result={file}`；且前缀按 **provider 兜底表**（claude_code→`C`、codex→`O`、codearts_agent→`A`）——文档的字母与格式双错 | **不成立**（格式） |
| 「解析 'A.ACK' 前缀 → 确认 ACK」 | `is_explicit_ack_source` 校验的是**渠道身份**（`("cli-ack","chat-ack")` 前缀表）：`"cli-ack"`→True、`"A.ACK|task=…"`→**False**、文档格式→**False**（实测） | **不成立**（机制） |
| 「验证产出文件存在 → 更新 Task.status」 | 落在 `result_consistency_audit` + ack bridge：见 2.3 | 部分 |

### 2.3 看门狗与审计（真闭环 ✓）

- `collect_ack_watchdog_candidates` 实测（scratch 状态机）：静默超阈任务 T1 **正确揪出**；已 ACK 的 T3、终态 T2 正确排除；时间闸生效（阈值 99999s 时零候选）。判档**成立**。
- `run_terminal_result_consistency_audit` 实测（注意状态文件真名是 **`logs/collaboration_state.json`**）：2 个终态任务入审——有产物者 consistent ✓、缺产物者 `missing_result_file`（"terminal task missing result_file"）✓；非终态正确跳过。判档**成立**。
- stop_check 甚至能揪「completed 但缺显式 ACK」的任务并给出补票命令（见 §4.4）——闭环比文档更深。

## 3. 范例四实测（NotebookLM + 多源聚合）

| 声明 | 实测 | 判档 |
|---|---|---|
| `notebooklm: "fallback" (默认)` | `integration_flags.py` 真值 `IntegrationMode.FALLBACK` ✓ | **成立** |
| 「MCP 健康检查 → connected ✓ → 切换 REAL」 | 本机无 notebooklm-mcp：`connect()` 实测「MCP工具不可用→回退到Mock」；**REAL 通路未验证**（无凭据不背书） | **部分成立**（fallback 真，REAL 未证） |
| 返回真实片段 fragment_1/2/3（950 万辆等） | `query_knowledge` mock 返回 `"[NotebookLM Mock响应] 关于{topic}的知识..."` + 固定假源 `['document1.pdf','document2.docx']`；`fragments` 字段**不存在** | **不成立**（mock 层） |
| 缓存：`notebooklm_cache.py` 相似度匹配 | **文件不存在**（integrations/ 下无此模块）；同题两次响应一致是 mock 确定性输出 | **不成立** |
| 多源聚合：去重→保留高置信→置信度评分 | `KnowledgeAggregator.aggregate` 管道真跑：`_select_relevant_sources → deduplicate → cross_validate → merge → calculate_confidence`；**跨源验证真**（两源共现「950 万辆」→ true，单源「2026 补贴」→ false）；但去重是**精确级**（s1/s2 重叠行仍双份保留），merged 是 `[Source N: type]` 标签拼接，overall_confidence 本轮得 1.0（非文档的 0.95/0.75 分级样例） | **部分成立**（管道真、细节与样例漂移） |
| 知识图谱/研究工作流/学习推荐 | 文件存在（kgraph/research_workflow/learning/recommender），本轮未跑 | 文件真值成立、行为未测 |

## 4. 范例五实测（四 Hook，stdin JSON + scratch workspace 真跑）

| # | Hook | 实测行为 | 判档 |
|---|---|---|---|
| 1 | session_inject | exit 0，输出 Claude Code `additionalContext` JSON：`active_tasks: 1 / completed_tasks: 1 / last_intent: 设计用户认证模块 / intent_category: implementation / lead_agent: user` + status.md 全文嵌入——任务计数+意图分类注入 ✓（冲突警告未触发：本轮无冲突 fixture） | **成立** |
| 2 | spawn_agent_preflight | 输出 `permissionDecision: "deny"` + 原因「parent_task_id is required for spawn_agent delegation」——**预检真拦截**（文档的「预检失败→阻止 spawn_agent」✓，拒绝理由更细） | **成立** |
| 3 | pre_compact | `.cc-claude-codex/snapshots/<ts>-status.md` + `<ts>-state.json` 快照 ✓（`shutil.copy2`）；**无哈希计算/元数据**（文档「记算文件哈希 a3b2c1…」不成立）；目录是 `.cc-claude-codex/snapshots/` 非 `logs/snapshots/` | **部分成立** |
| 4 | stop_check | 有未完成 → **exit 2 拦截**，消息含：status.md 未完成项 + 活跃任务 + **显式 ACK 缺失清单** + 补票命令 `python3 -m ai_collab.cli ack --task-id … --ai … --status ok` + 🛑 标记提示；干净 workspace → exit 0 放行 ✓。文档的「三选一（ACK/标 blocked/force-exit）」措辞与真实输出不同（真实无 force-exit 选项） | **大部分成立** |

## 5. 环境与复现

- 引擎/模块层：`/Users/raymondna/miniforge3/bin/python`（aiohttp 等依赖在 conda）；harness 三个（consensus+soul / ack / hooks）+ notebooklm 聚合，均 scratch workspace、零 repo 污染（`.reviews/` 冒烟数据已清）。
- mock/fallback 为**默认生产模式**（`integration_flags.py: FALLBACK = production default`）；REAL 通路本轮全部如实标注未验证，不以 mock 结果冒充 REAL。
- 状态机注意：StateManager 读 **`logs/collaboration_state.json`**（`config.stateFile` 默认），写错层级会得到 audited_count=0 的假阴性（本轮已踩已修）。

## 6. 结论表（文档 → 实盘一句话）

| 文档核心叙事 | 实盘 |
|---|---|
| 共识引擎「提论点/去重/0.95 置信」 | 拼接 + 固定 mock 置信度；真算法在 multi_source 聚合器 |
| 「A.RUN→架构师」 | 反了：A.RUN→AGENT_EXEC |
| 「A.ACK 前缀解析」 | 渠道身份校验（cli-ack/chat-ack）+ 管道格式 ACK 行 |
| NotebookLM 真实片段 + 相似度缓存 | mock 固定片段；缓存模块不存在 |
| 快照哈希校验 | copy2 无哈希 |
| 幂等/看门狗/审计/预检拦截/退出拦截 | **全部真** |
