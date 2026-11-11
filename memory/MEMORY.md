# Memory Index

## Project
- [CI 隔离陷阱——「本地绿、CI 红」的用例依赖本机 HOME 状态](feedback_ci_isolation_trap.md) — 2026-10-24 实测——tests/unit/test_codearts_bridge_deliver.py 有 7 条用例依赖开发机上真实安装的 CodeArts Doer kernel 与凭据文件，开发机全绿而 CI runner 全红；本仓已加空 HOME 隔离守护
- [AI Collaboration System 项目状态与技术债追踪](project.md) — AI Collaboration System 项目状态、技术债、并行协作风险与测试环境陷阱
- [Claude Code 对未注册自定义模型按 200k 上下文窗口假设](project_claude_code_model_window.md) — 模型 ID 为 MiniMax-M3.1-Flash 等未在 Claude Code 注册表内的自定义模型时，报 unrecognized_model 并按 200k 窗口计算；属噪音告警而非任务失败
- [CLI 退出码传递与 R6 禁止修改清单](project_cli_exit_code.md) — 2026-10-23 曾发现 ai_collab/cli/__main__.py 丢弃 main() 返回值，同日已由 commit a938cd8 正式修复（TASK-P1-CLI-EXITCODE-001）；2026-10-24 进程级复验通过——该缺陷已不存在，「因禁改清单而未修」的记忆不得再当作现状引用
- [派单链路的模型降级与可观测性目标](project_dispatch_model_fallback.md) — 2026-10-23 起推进的 P1 目标——指定模型不可用时自动降级到模型池下一候选、投递回执落盘、报告区分「请求的模型」与「实际用的模型」
- [双 Agent（CodeArts + Claude Code）配置一致性与实时同步核查](project_dual_agent_config_sync.md) — 2026-10-22 核查结论：CodeArts 与 Claude Code 的规则文件/记忆目录既无 symlink 也无任何同步机制；治理门禁期望根 AGENTS.md 但缺失；用户目标是「配置信息一致 + 链接 + 实时同步」
- [体检工具链加固工单背景（密钥扫描器误报、check_git 假绿）](project_healthcheck_tooling_debt.md) — 2026-10-24 派单 TASK-P1-HEALTHCHECK-TOOL-HARDEN-001 的背景问题——密钥扫描器误报 237 条需降到 0、check_git() 缺 origin/main 存在性判断造成体检假绿、check_health_rules() 对长期经验条数统计不准
- [IDE 同一工作区活跃 Agent 会话上限 3 个](project_ide_session_limit.md) — IDE 限制同一工作区同时活跃的 Agent 会话最多 3 个，超限报「并发会话数已达上限(3个)，请关闭部分会话后重试」；kernel /session 元数据可列全部会话但看不出哪些在运行
- [project-intervention-delivery-states](project_intervention_delivery_states.md) — 干预队列的投递状态语义——入队必须用 delivery_mode="manual"（pending_operator_delivery），用 "bridge" 会被在途过滤器静默跳过，投递根本不会发生且不报错
- [OpenSpec CLI 1.11.0 的 legacy 边界与本仓现行接线形态](project_openspec_cli_wiring.md) — 2026-10-24 实测——openspec 1.11.0 把 openspec/AGENTS.md 当 legacy 并在 init --force 时删除，根 CLAUDE.md 的 OPENSPEC:START/END managed block 也是 legacy（1.11.0 主动删除它）；本仓现行形态是 openspec/config.yaml + .claude/skills/openspec-* + .codeartsdoer/skills/openspec-*
- [历史 Prompt Pack 是空壳（2026-11-03 考古结论）](project_pack_shell_empty.md) — 【2026-11-03 考古结论，随后已改观】当时 16 个历史包共 62 个 AI 步骤、0 个有 prompt_template，Chrome 侧空串直送 AI。现状：阶段一补了 xiaohongshu_knowledge_creator.json（7 条 prompt_template），阶段三把 15 个空壳移入 packs/templates/，packs/examples/ 只剩 2 个能跑的包。要点：能过校验 ≠ 能跑出产物
- [Python 侧与 Chrome 侧的协议取值域互不相交（2026-11-03 审计根因）](project_protocol_layer_mismatch.md) — 校验器/Schema 白名单只认 local/analysis/generation/validation/fusion/tracking，Chrome 执行器只认 local/ai，交集只有 local；external-user-smoke.json 唯一 ERROR 是 Invalid step type: ai；统一路线属产品取舍待用户拍板
- [Chrome 扩展真机验证只能由用户在真实 Chrome 完成](project_real_chrome_verification.md) — 2026-11-02 实测——IDE 内置 browser 工具只能开 URL、不能读页/点击/加载扩展，故永远无 [Prompt Pack] 日志，不能用于 L2；本机 9222 端口虽监听但 /json 返回 404，无法接管外部 Chrome；L2 的「人点发送」必须用户本人在真实 Chrome 完成
- [产品路线 A/B 决策门禁（真机 3 平台回归 + 第一个外部用户）](project_route_decision.md) — 产品路线 A/B 决策门禁。🔧 2026-11-11 12:18 用户裁定：**平台范围收缩为 5 个**——只保留 qianwen / yuanbao / chatglm / yiyan / kimi，其余（deepseek / longcat / gemini / chatgpt / claude / dots）全部暂时冻结不去碰；此裁定推翻 06:10 的「只推 deepseek 和 longcat」。13:02 活跃 5 站同日完整回归（RMR-2026-11-11-03）8/8 全 pass。⇒ **活跃 5/5 全 pass，但分母仍记 10，5/10 不因裁定上升**；冻结项仍记 fail / not-run，不得算作已验证。⚠️ 冻结 ≠ 缺陷修好：step_8 长会话尾部撞墙属 Pack 结构假设问题，在活跃站依然潜伏。dots 记 not-run、不计入分母，立项亦冻结。⚠️ 本文件今日内容曾因误改镜像被覆盖，已按会话原文复原；07:50 节前半段原文不可恢复，详见文内重建声明。
- [任务契约 change_id 白名单与非法值的修正方式](project_task_change_id_whitelist.md) — ai_collab 任务契约校验器对 change_id 只认 bugfix/no-spec、legacy/task-contract-migration 或 openspec 真实变更；工单写 feature/no-spec 会被 tasks update 拒收（invalid=[change_id]），需用 --change-id 修正并留痕
- [仓库跟踪了残缺 node_modules，worktree 与 npm 都会被误导](project_worktree_node_modules_trap.md) — git 跟踪的 node_modules 只有约 129 个文件（约 5.3MB），完整依赖约 71MB/2600 文件；worktree add 会检出这份假依赖，npm 误判已装，npm run build 报一堆与真实原因无关的错

## Feedback
- [ACK/receipt 必须由 CLI 生成且先 RUN-RESET 再 RUN](feedback_ack_cli_generated.md) — 派单流程硬性规范——ACK/receipt 禁止手写，须用 python3 -m ai_collab.cli ack ... 生成并原样回复；RUN 静默无 ACK 时先 A.RUN-RESET 再 A.RUN
- [回答形态规范（目标反推清单 / 就绪度按线判定 / 两者的适用边界）](feedback_answer_shape.md) — 用户已给明确目标时应反推应做项清单而非并列可选项；问就绪度时按工作线逐项判定再给二选一授权；两者适用场景不同，不可混用
- [Chrome host 匹配里裸域只等于自己——www 变体必须单列](feedback_chrome_host_pattern.md) — manifest 的 host 模式写 https://qianwen.com/* 时，Chrome 只匹配该域本身、不匹配 www.qianwen.com（只有 *. 才通配）⇒ 内容脚本根本不注入；host_permissions 与 content_scripts.matches 须收敛成同一份清单
- [CodeArts 派单执行的工具约束（禁 write/edit、禁派生代理、写文件用 bash heredoc）](feedback_codearts_session_tooling.md) — 真机实测 CodeArts 会话中 write/edit 工具与派生 subagent 会卡死并中止会话；派单任务写文件一律用 bash heredoc
- [CodeArts 会话工具约束（禁 write/edit、禁派生子代理；并行 bash 改单条逐个执行）](feedback_codearts_tooling_constraints.md) — 真机实测 CodeArts 会话中 write/edit 与派生 subagent 会卡死并中止会话，写文件一律用 bash heredoc；并行批次中单条命令失败可致整批 abort，校验多路径改用单条逐个执行
- [投递结果判定口径——等回执超时≠投递失败](feedback_delivery_outcome_semantics.md) — 派单投递中「等回执超时」不得直接判失败；必须先向 kernel 核实消息是否被接受，否则误报 failed 会触发重投并在对方新开会话，造成双会话并发改同一工作区
- [CodeArts 派单执行全流程规范（新鲜度 → RUN-RESET → RUN → 结果文件 → CLI ACK）](feedback_dispatch_execution_protocol.md) — 派单流程硬性规范——payload 先校验新鲜度（≤5 分钟）、系统级 RUN 只许单条 cli run、ACK/receipt 禁手写须用 cli ack 生成、结果文件须含 PROTOCOL §7.4 四段+可解析状态行+测试结论小节、终态收口 completed
- [派单 payload 必须先校验新鲜度，系统级 RUN 只允许单条 cli run](feedback_dispatch_payload_freshness.md) — 收到派单 payload 后先比对 logs/task_dispatch_report.json 的 generated_at（≤5 分钟），过期用 cli trigger 一键重生成；系统级 RUN 只许 python3 -m ai_collab.cli run，禁止拆成 dispatch/receipt/benefit 串联
- [方案选型前先做可行性实测，不凭直觉论证](feedback_empirical_test_before_solution_choice.md) — 用户要求「先做链接可行性实测，再定软链还是生成方案」；涉及技术选型时先跑实测拿到退出码/行为级真证，再给判定与方案
- [严格输出格式约束须逐字照办](feedback_exact_output_format.md) — 用户给出字数/格式/字符集约束（如只回一个词）时，输出必须仅含被要求内容，不加解释、前后缀或 Markdown 包裹
- [失败不许跨层吞掉——「执行成功」比「报错」更危险](feedback_failure_must_not_be_swallowed.md) — 内容脚本如实回 {success:false}，执行器却无条件置 success=true，后台再一律回 success:true ⇒ popup 显示「执行成功」而产物是空的；修法是各层都看真实状态，且执行器的校验要放在 try/catch 外面
- [静态 fixture 只有结构没有行为——仿真站点得仿行为](feedback_fixture_needs_behavior.md) — 手写 mock 与真机快照都只还原 DOM 结构，不含「框架模型」这类行为⇒「DOM 里有字」冒充「模型收到了」；修法是把站点行为抽成一份共享仿真（模型/选区/按钮启用条件），让矩阵、接线测试、注入守护共用同一份
- [按用户既定目标反推应做项，而非并列可选项](feedback_goal_driven_backlog.md) — 用户已给出明确目标时，应从目标逐条反推应落地项并给出「目标↔项↔依据↔优先级」映射；禁止退回到并列的「你可以选 1/2/3」式可选项
- [交付报告禁列流程仪式（仪式税），门禁改分层触发](feedback_no_ceremony_tax.md) — RESULT/closeout 不得列举 Skill 触发与门禁遵循情况；closeout 只写 5 行；门禁按提交/周/里程碑分层触发
- [通过率提升 ≠ 交付价值（绿门禁假修复的判别准则）](feedback_no_green_faking.md) — 让校验器变绿但产品行为没变的"修复"是假修复（空壳包补 name 即典型）；提效型修复必须同时验证"真能执行/产出物"，否则不予采纳
- [对外可见动作需要当前会话内的明确授权](feedback_outward_actions_need_in_session_approval.md) — 2026-10-24 实测——gh pr create 被 auto-mode 分类器以「Unrequested Commit in a Connected App」拦下，理由是授权只出现在被压缩的会话摘要里而非当前轮次；解决办法是先用 AskUserQuestion 拿到用户当场的明确授权再重试
- [并行 bash 调用 abort 防范（单条逐个校验优于并行混合）](feedback_parallel_bash_abort.md) — 并行 bash 调用中若有一条命令对不存在目录报错，可能导致整批 abort；校验多路径时改用单条逐个执行
- [动手实现前给「按线就绪度判定」，不给全局二元答案](feedback_readiness_gate_before_coding.md) — 用户会追问「是否已具备动手条件/是否还需更多实测」；期望按工作线分别判定就绪度，并逐项列出还差什么、类型、阻塞面，最后给二选一授权而非直接开干
- [报告要留痕：先认错、标出被改写的判断、决策留给用户](feedback_report_traceability.md) — 用户认可"留痕比好看重要"——改过的结论用 🔧 就地标注、旧动作表保留并指向修正版、错误先明确认领；建议收敛到唯一零风险动作，产品取舍列成互斥选项交用户拍板
- [RESULT 结果文件的契约校验与终态一致性要求](feedback_result_file_contract.md) — 结果文件除 PROTOCOL §7.4 四段标题外还需可解析的状态行与测试结论小节，否则 tasks validate-contract 与一致性审计判不合格；任务终态须收口为 completed
- [结果文件/文档引用扫描触发串会自命中（密钥扫描器视角）](feedback_result_file_self_scan_hit.md) — collaboration/results 下的结果文件本身在密钥/PII 扫描范围内，文档中原样内联扫描触发串或正则片段会被自家扫描器自命中；须改为间接描述 + 白名单自豁免，写完立即自扫确认为 0
- [富文本编辑器的内容在框架模型里——DOM 有字不等于站点收到了](feedback_rich_text_editor_model.md) — Slate/ProseMirror/Quill 把内容存在自己的模型中，execCommand 只动 DOM ⇒ 站点读到「用户没输入」⇒ 发送按钮保持 disabled ⇒ 点它等于没点；修法是派发真的 beforeinput，判据靠零宽叶子等**结构**信号，另注意 role="textbox" 分支顺序与后台标签页不用 rAF
- [service worker 里没有 window——页面侧函数不能直接调](feedback_service_worker_no_window.md) — MV3 的 service worker 里 typeof window === "undefined"，后台调页面侧的 adapter.detect() 会抛 ReferenceError 并挂掉整个 onMessage 处理器⇒永远不 sendResponse⇒扩展在任何站点上都拿不到适配器且不报错
- [排查受阻时先穷尽自判手段，只留一次人证动作](feedback_single_user_action_debugging.md) — 用户反馈「还是没有」时不要继续盲改、也不要反复让其回报中间态日志；先做一次可判定的二分判定并穷尽 Agent 侧可自动核验的环节，把不可替代的人证动作收敛成一次并写清成功标志
- [前端不该是第二个判定方——「什么算 Pack」只能有一处说了算](feedback_single_validation_authority.md) — 导入界面比后台更严（前端只认 {packs:[...]}、后台两种形状都收）⇒ 照指南导入单个 Pack 文件直接报「文件格式错误」；前端多一道闸 = 两个判定方 = 迟早漂移
- [项目体检测试失败诊断流程](feedback_test_failure_diagnosis_flow.md) — 2026-11-09 项目体检中发现的测试失败诊断与修复模式——测试断言未对齐新架构、工作区未提交改动导致测试失败
- [测试门禁分层原则（硬门禁对齐真证，软警告用于理想规范）](feedback_test_gate_design.md) — 设计测试门禁时，硬门禁只放基线项，"应当有"特性降级为软警告；测试不应造假以通过门禁
- [工具校验器报错不等于文件有错——用权威解析器复核后再动手](feedback_validator_false_positive.md) — 编辑器/内置校验器对 YAML 等结构化文件报错可能系工具自身故障；先用权威解析器（如 Python yaml.safe_load）复核，勿因误报改动本已正确的文件
- [同步类改动须同时验「静态接线」与「行为级加载」，并做漂移注入闭环](feedback_verification_static_vs_behavioral.md) — 配置/记忆同步类交付的验证形态：静态 grep 接线 ≠ 行为级生效；漂移须同时验证「能检测」与「能修复」；验证脚本要可复用
- [引用文件路径与编号前必须先在仓库里核对存在性](feedback_verify_before_citing_paths.md) — 写手册/清单时凭印象写出的文件路径、脚本名、缺口编号在仓库中查无此物；动手落盘前先 Glob/Grep 核对真实路径与编号口径，并写明「不存在」而非假装有
- [改动先核磁盘真证再宣布（用户不认口头承诺）](feedback_verify_disk_before_claim.md) — 用户要求"先核磁盘——你说的改动我要看到才认"；改完必须核实际文件内容与所在分支，成本估算要实测不要拍脑袋
- [工作区清理与提交策略](feedback_workspace_cleanup_strategy.md) — 2026-11-09 项目体检中的工作区清理模式——未跟踪目录加入 gitignore、Conventional Commits 提交、提交前验证
- [重活校验跑在独立 worktree，不碰用户工作区](feedback_worktree_isolation.md) — 用户工作区有未提交改动时，全套校验/构建/大 diff 必须放 git worktree 里做；结论必须标注基线 commit（HEAD 还是 main），差异大时以目标分支为准重查

## Reference
- [laya 本地决策引擎服务（127.0.0.1:8421）](reference_laya_decision_engine.md) — 用户本地部署的 MLX 双模型决策引擎，区别于通用对话 LLM，用于结构化决策问题（分类/打分/真伪判断）
- [本地 LLM 决策建议服务（127.0.0.1:1234）](reference_local_llm_endpoint.md) — 用户调用的本地 LLM 服务地址，用于对"需确认的决策点"给出建议
- [user](user.md) — 用户角色与偏好信息
