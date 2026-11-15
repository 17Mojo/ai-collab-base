# task-contract Specification

## Purpose
TBD - created by archiving change migrate-session-identity. Update Purpose after archive.

## Requirements

### Requirement: 工单身份声明

工单契约 SHALL 以 `session_id` 与 `model_id` 作为执行主体身份，两者合起来回答「谁在哪个模型上
完成了这个工单」。在身份成为必填项的时间切点之后创建的工单，缺失任一字段 SHALL 判定为契约不
合法；切点之前创建的工单 SHALL 判定为历史工单（legacy），不因缺失而判错。

#### Scenario: 新工单声明了完整身份

- **WHEN** 切点之后创建的工单同时给出 `session_id` 与 `model_id`，且两者格式合法
- **THEN** 契约校验判定该项通过
- **AND** 输出中把该工单计为「身份已声明」

#### Scenario: 新工单缺失身份

- **WHEN** 切点之后创建的工单缺少 `session_id` 或 `model_id`
- **THEN** 契约校验判定为不合法，并点名缺失字段
- **AND** 不得因为存在 `assignee`（厂商名）而判定通过

#### Scenario: 历史工单缺失身份

- **WHEN** 切点之前创建的工单没有 `session_id` / `model_id`
- **THEN** 契约校验不因该原因判错
- **AND** 该工单被计入 `legacy_identity` 计数并在输出中显式给出
- **AND** 不得为该工单编造身份值

#### Scenario: 身份格式非法

- **WHEN** `session_id` 或 `model_id` 存在但含空白、超长或非法字符
- **THEN** 契约校验判定该项不合法，并区分「缺失」与「格式非法」两种原因

### Requirement: 身份与路由分离

系统 SHALL 区分「身份」与「路由」两类信息：身份（`session_id` / `model_id`）是契约层事实，
路由（`assignee`，即提供商标签）是运行时投递键。工单 SHALL 允许只声明身份，由系统按会话注册表
反查路由键；反查不到时 SHALL 拒绝创建并要求显式给出路由键，而不是静默留空。

#### Scenario: 只给身份时反查路由键

- **WHEN** 创建工单时只给出 `session_id` / `model_id`，且该会话已在会话注册表中登记
- **THEN** 系统按注册表反查得到该会话的 `assignee` 并写入工单
- **AND** 输出中说明该路由键来自反查而非显式声明

#### Scenario: 反查不到路由键

- **WHEN** 创建工单只给出 `session_id`，但注册表中没有该会话
- **THEN** 系统拒绝创建工单并提示显式给出 `assignee` 或先登记会话
- **AND** 不得写入空的 `assignee` 让下游路由失败在更远的地方

### Requirement: 身份迁移审计

系统 SHALL 提供迁移审计入口，逐条给出每个工单的身份状态：已声明、可从会话注册表反查、
不可反查（历史）。审计 SHALL 默认只读；只有在反查确实可用时才允许写入，且写入内容 SHALL
仅来自注册表事实。

#### Scenario: 审计不写入

- **WHEN** 以只读方式运行迁移审计
- **THEN** 不修改任何工单文件或状态账本
- **AND** 输出给出三类计数

#### Scenario: 反查可用时才回填

- **WHEN** 以写入方式运行迁移审计，且某工单的会话在注册表中可查
- **THEN** 该工单被补上注册表中的 `session_id` 与对应路由键
- **AND** 反查不到的工单保持不变，不被填入猜测值
