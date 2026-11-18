# active-platform-registry Specification

## Purpose
TBD - created by archiving change replace-qianwen-with-stepfun. Update Purpose after archive.

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
