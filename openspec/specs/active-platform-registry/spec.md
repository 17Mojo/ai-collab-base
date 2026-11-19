# active-platform-registry Specification

## Purpose
把真机自动化的平台范围绑定到用户裁定，而不是脚本碰巧能访问到哪些站：活跃白名单只有一个代码事实源，平台退出目标源不等于删除生产支持；未经有效检验的命题不得写成已解决，现场判断与磁盘证据必须分层陈述，避免把一次「没跑到生效点」误记成「边界无效」。

## Requirements

### Requirement: 活跃真机白名单由用户裁定并落在代码里

活跃白名单 SHALL 是唯一事实源 `ACTIVE_PLATFORM_IDS`，并在用户改判时同步更新。
被移出的站点 SHALL NOT 被真机驱动默认打开、预检或发包；其生产 adapter
MUST NOT 因此被删除（生产支持与真机白名单是两件事）。

#### Scenario: 用 stepfun 替换 qianwen

- **WHEN** 白名单中的 qianwen 被 stepfun 替换
- **THEN** `PLATFORM=qianwen` 默认被冻结闸门拒绝
- **AND** `PLATFORM=stepfun` 默认放行且回执 `unfrozenBy=null`
- **AND** qianwen adapter 仍能通过平台注册一致性测试

### Requirement: 新平台先有登录事实再登记

新平台 SHALL 先由真人完成登录并留下可复核的账号信号，再登记进生产与测试注册表。
仅凭「页面有输入框」MUST NOT 判定为已登录；游客态首页误判 SHALL 被记录并更正，
不得静默删掉假阳性证据。

#### Scenario: stepfun 游客态假阳性

- **WHEN** 未登录的 stepfun 首页出现输入框
- **THEN** 只靠 composer 的登录判定 MUST NOT 作为登记依据
- **AND** 真人确认标记与账号信号出现后，才写入登录证据

#### Scenario: 登录由真人完成

- **WHEN** 脚本打开 stepfun 等待真人登录
- **THEN** 脚本 SHALL NOT 点击发送、导入 Pack 或绕过验证码
- **AND** 登录态证据 SHALL 记录 profile 路径与采样时间

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
