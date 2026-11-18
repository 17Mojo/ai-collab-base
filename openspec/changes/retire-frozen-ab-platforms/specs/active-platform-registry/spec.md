## ADDED Requirements

### Requirement: 目标源退出是治理定性，不等于删除平台支持

平台被裁定退出目标源时，系统 SHALL 把该裁定记录在结果报告与缺口台账中，
并保留其生产 adapter 与代码级冻结事实；MUST NOT 为了表达「退出」而改写白名单常量、
冻结常量或闸门语句（它们是变异锚点，改动会削弱守卫）。

#### Scenario: deepseek / longcat 退出目标源

- **WHEN** 用户裁定 deepseek / longcat 不适合作为目标网络源
- **THEN** `ACTIVE_PLATFORM_IDS` 仍是不含这两站的 5 站白名单，闸门默认拒绝它们
- **AND** 结果报告与 `known_gaps.json` 记录退出理由与裁定人
- **AND** 两站生产 adapter 仍保留，平台注册一致性测试不删站

### Requirement: 未获有效检验的命题不得写成已解决

当 A/B 对照因实验对象在自变量生效之前就失败而无法检验命题时，
结果报告 SHALL 把它记为「未获有效检验」，MUST NOT 记为「边界无效」的实测结论，
更 MUST NOT 记为「命题成立/问题已解」。关闭缺口时 SHALL 同时写明关闭理由与目标源状态变化。

#### Scenario: step_5 撞墙早于 step_8 边界生效点

- **WHEN** A/B 两轮都在 `step_5_boundary` Response timeout 且 `sessionResets=[]`
- **AND** `fresh_session` 只声明在 `step_8_output`
- **THEN** 报告 SHALL 记 `packCompleted=FAIL` / `resetActuallyHappened=FAIL（无机会）`
- **AND** verdict 记为「命题未获支持 / 未获有效检验」，不得写「边界试过无效」
- **AND** 缺口关闭理由 SHALL 含「目标源退出」或「命题失去观察对象」

### Requirement: 现场判断与磁盘证据分层陈述

结果报告 SHALL 区分「回执里有信号的实测结论」与「用户现场判断的产品裁定」；
现场判断可作为目标源取舍依据，但 MUST NOT 写成实测证实的平台行为。

#### Scenario: 反自动化判断无回执信号

- **WHEN** 用户判断某站防范自动化严格，而 A/B 回执只有 Response timeout、
  没有验证码 / WAF / 风控拦截信号
- **THEN** 报告 SHALL 把反自动化标为「用户现场判断 / 产品裁定依据」
- **AND** 磁盘可证部分只写 Response timeout 与撞墙位漂移现象
