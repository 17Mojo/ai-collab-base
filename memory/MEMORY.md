# Memory Index

## Project
- [AI Collaboration System 项目状态与技术债追踪](project.md) — AI Collaboration System 项目状态、技术债、并行协作风险与测试环境陷阱
- [Claude Code 对未注册自定义模型按 200k 上下文窗口假设](project_claude_code_model_window.md) — 模型 ID 为 MiniMax-M3.1-Flash 等未在 Claude Code 注册表内的自定义模型时，报 unrecognized_model 并按 200k 窗口计算；属噪音告警而非任务失败
- [CLI 退出码传递与 R6 禁止修改清单](project_cli_exit_code.md) — 2026-10-23 曾发现 ai_collab/cli/__main__.py 丢弃 main() 返回值，同日已由 commit a938cd8 正式修复（TASK-P1-CLI-EXITCODE-001）；2026-10-24 进程级复验通过——该缺陷已不存在，「因禁改清单而未修」的记忆不得再当作现状引用
- [派单链路的模型降级与可观测性目标](project_dispatch_model_fallback.md) — 2026-10-23 起推进的 P1 目标——指定模型不可用时自动降级到模型池下一候选、投递回执落盘、报告区分「请求的模型」与「实际用的模型」
- [双 Agent（CodeArts + Claude Code）配置一致性与实时同步核查](project_dual_agent_config_sync.md) — 2026-10-22 核查结论：CodeArts 与 Claude Code 的规则文件/记忆目录既无 symlink 也无任何同步机制；治理门禁期望根 AGENTS.md 但缺失；用户目标是「配置信息一致 + 链接 + 实时同步」
- [体检工具链加固工单背景（密钥扫描器误报、check_git 假绿）](project_healthcheck_tooling_debt.md) — 2026-10-24 派单 TASK-P1-HEALTHCHECK-TOOL-HARDEN-001 的背景问题——密钥扫描器误报 237 条需降到 0、check_git() 缺 origin/main 存在性判断造成体检假绿、check_health_rules() 对长期经验条数统计不准
- [project-intervention-delivery-states](project_intervention_delivery_states.md) — 干预队列的投递状态语义——入队必须用 delivery_mode="manual"（pending_operator_delivery），用 "bridge" 会被在途过滤器静默跳过，投递根本不会发生且不报错
- [产品路线 A/B 决策门禁（真机 3 平台回归 + 第一个外部用户）](project_route_decision.md) — AI Collaboration System 路线拍板（路线 A Prompt Pack 面向创作者 vs 路线 B Agent 协作控制面产品化）唯一缺失的真证是「真机 3 平台回归 + 第一个外部用户」，截至 2026-10-22 实验未启动
- [任务契约 change_id 白名单与非法值的修正方式](project_task_change_id_whitelist.md) — ai_collab 任务契约校验器对 change_id 只认 bugfix/no-spec、legacy/task-contract-migration 或 openspec 真实变更；工单写 feature/no-spec 会被 tasks update 拒收（invalid=[change_id]），需用 --change-id 修正并留痕

## Feedback
- [ACK/receipt 必须由 CLI 生成且先 RUN-RESET 再 RUN](feedback_ack_cli_generated.md) — 派单流程硬性规范——ACK/receipt 禁止手写，须用 python3 -m ai_collab.cli ack ... 生成并原样回复；RUN 静默无 ACK 时先 A.RUN-RESET 再 A.RUN
- [回答形态规范（目标反推清单 / 就绪度按线判定 / 两者的适用边界）](feedback_answer_shape.md) — 用户已给明确目标时应反推应做项清单而非并列可选项；问就绪度时按工作线逐项判定再给二选一授权；两者适用场景不同，不可混用
- [CodeArts 派单执行的工具约束（禁 write/edit、禁派生代理、写文件用 bash heredoc）](feedback_codearts_session_tooling.md) — 真机实测 CodeArts 会话中 write/edit 工具与派生 subagent 会卡死并中止会话；派单任务写文件一律用 bash heredoc
- [CodeArts 会话工具约束（禁 write/edit、禁派生子代理；并行 bash 改单条逐个执行）](feedback_codearts_tooling_constraints.md) — 真机实测 CodeArts 会话中 write/edit 与派生 subagent 会卡死并中止会话，写文件一律用 bash heredoc；并行批次中单条命令失败可致整批 abort，校验多路径改用单条逐个执行
- [投递结果判定口径——等回执超时≠投递失败](feedback_delivery_outcome_semantics.md) — 派单投递中「等回执超时」不得直接判失败；必须先向 kernel 核实消息是否被接受，否则误报 failed 会触发重投并在对方新开会话，造成双会话并发改同一工作区
- [CodeArts 派单执行全流程规范（新鲜度 → RUN-RESET → RUN → 结果文件 → CLI ACK）](feedback_dispatch_execution_protocol.md) — 派单流程硬性规范——payload 先校验新鲜度（≤5 分钟）、系统级 RUN 只许单条 cli run、ACK/receipt 禁手写须用 cli ack 生成、结果文件须含 PROTOCOL §7.3 四段+可解析状态行+测试结论小节、终态收口 completed
- [派单 payload 必须先校验新鲜度，系统级 RUN 只允许单条 cli run](feedback_dispatch_payload_freshness.md) — 收到派单 payload 后先比对 logs/task_dispatch_report.json 的 generated_at（≤5 分钟），过期用 cli trigger 一键重生成；系统级 RUN 只许 python3 -m ai_collab.cli run，禁止拆成 dispatch/receipt/benefit 串联
- [方案选型前先做可行性实测，不凭直觉论证](feedback_empirical_test_before_solution_choice.md) — 用户要求「先做链接可行性实测，再定软链还是生成方案」；涉及技术选型时先跑实测拿到退出码/行为级真证，再给判定与方案
- [严格输出格式约束须逐字照办](feedback_exact_output_format.md) — 用户给出字数/格式/字符集约束（如只回一个词）时，输出必须仅含被要求内容，不加解释、前后缀或 Markdown 包裹
- [按用户既定目标反推应做项，而非并列可选项](feedback_goal_driven_backlog.md) — 用户已给出明确目标时，应从目标逐条反推应落地项并给出「目标↔项↔依据↔优先级」映射；禁止退回到并列的「你可以选 1/2/3」式可选项
- [交付报告禁列流程仪式（仪式税），门禁改分层触发](feedback_no_ceremony_tax.md) — RESULT/closeout 不得列举 Skill 触发与门禁遵循情况；closeout 只写 5 行；门禁按提交/周/里程碑分层触发
- [并行 bash 调用 abort 防范（单条逐个校验优于并行混合）](feedback_parallel_bash_abort.md) — 并行 bash 调用中若有一条命令对不存在目录报错，可能导致整批 abort；校验多路径时改用单条逐个执行
- [动手实现前给「按线就绪度判定」，不给全局二元答案](feedback_readiness_gate_before_coding.md) — 用户会追问「是否已具备动手条件/是否还需更多实测」；期望按工作线分别判定就绪度，并逐项列出还差什么、类型、阻塞面，最后给二选一授权而非直接开干
- [RESULT 结果文件的契约校验与终态一致性要求](feedback_result_file_contract.md) — 结果文件除 PROTOCOL §7.3 四段标题外还需可解析的状态行与测试结论小节，否则 tasks validate-contract 与一致性审计判不合格；任务终态须收口为 completed
- [结果文件/文档引用扫描触发串会自命中（密钥扫描器视角）](feedback_result_file_self_scan_hit.md) — collaboration/results 下的结果文件本身在密钥/PII 扫描范围内，文档中原样内联扫描触发串或正则片段会被自家扫描器自命中；须改为间接描述 + 白名单自豁免，写完立即自扫确认为 0
- [测试门禁分层原则（硬门禁对齐真证，软警告用于理想规范）](feedback_test_gate_design.md) — 设计测试门禁时，硬门禁只放基线项，"应当有"特性降级为软警告；测试不应造假以通过门禁
- [工具校验器报错不等于文件有错——用权威解析器复核后再动手](feedback_validator_false_positive.md) — 编辑器/内置校验器对 YAML 等结构化文件报错可能系工具自身故障；先用权威解析器（如 Python yaml.safe_load）复核，勿因误报改动本已正确的文件
- [同步类改动须同时验「静态接线」与「行为级加载」，并做漂移注入闭环](feedback_verification_static_vs_behavioral.md) — 配置/记忆同步类交付的验证形态：静态 grep 接线 ≠ 行为级生效；漂移须同时验证「能检测」与「能修复」；验证脚本要可复用

## Reference
- [laya 本地决策引擎服务（127.0.0.1:8421）](reference_laya_decision_engine.md) — 用户本地部署的 MLX 双模型决策引擎，区别于通用对话 LLM，用于结构化决策问题（分类/打分/真伪判断）
- [本地 LLM 决策建议服务（127.0.0.1:1234）](reference_local_llm_endpoint.md) — 用户调用的本地 LLM 服务地址，用于对"需确认的决策点"给出建议
- [user](user.md) — 用户角色与偏好信息
