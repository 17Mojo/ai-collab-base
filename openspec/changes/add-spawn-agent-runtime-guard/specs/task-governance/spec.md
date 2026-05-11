## ADDED Requirements

### Requirement: Configurable Spawn Agent Guard Policy

The system SHALL provide a project-level `spawnAgentGuard` policy in `.vscode/ai-collab.json` for Codex internal `spawn_agent` delegation guardrails.

#### Scenario: Init writes safe default spawn agent guard policy
- **WHEN** the project initializes or refreshes its default collaboration config
- **THEN** the generated `.vscode/ai-collab.json` SHALL include a `spawnAgentGuard` block
- **AND** the defaults SHALL reflect the documented rule that `spawn_agent` is limited to Codex single-parent-task internal delegation

#### Scenario: Missing guard block falls back to safe defaults
- **WHEN** a workspace config omits `spawnAgentGuard`
- **THEN** the system SHALL evaluate `spawn_agent` checks with safe default constraints
- **AND** SHALL NOT silently disable protected-path or parent-task validation

### Requirement: Spawn Agent Delegation Preflight Validation

The system SHALL validate a planned internal `spawn_agent` delegation before it is treated as governance-compliant.

#### Scenario: Codex single-parent-task write delegation passes preflight
- **WHEN** actor `codex` requests validation with one declared `parent_task_id`
- **AND** the declared write set is non-empty and does not violate configured constraints
- **THEN** the guard SHALL return an allowed result

#### Scenario: Codex single-parent-task read-only delegation passes preflight
- **WHEN** actor `codex` requests validation with one declared `parent_task_id`
- **AND** the delegation is explicitly marked read-only
- **AND** read-only delegation is allowed by policy
- **THEN** the guard SHALL return an allowed result

#### Scenario: Non-Codex or missing-parent delegation is blocked
- **WHEN** the guard receives a delegation plan from an actor outside `allowedLeadAgents`
- **OR** receives no declared `parent_task_id` while parent-task enforcement is enabled
- **THEN** the guard SHALL return a blocked result
- **AND** SHALL enumerate the violated rules

### Requirement: Protected Path And Active Task Conflict Rejection

The system SHALL block `spawn_agent` delegation plans that target protected governance artifacts or overlap active task write sets outside the declared parent task.

#### Scenario: Protected governance artifact is rejected
- **WHEN** the declared write set includes a configured protected path or protected prefix
- **THEN** the guard SHALL return a blocked result
- **AND** SHALL identify the violating path entries

#### Scenario: Active task write conflict is rejected
- **WHEN** the declared write set overlaps files owned by another active task in conflict-sensitive status
- **AND** the overlapping task is not the declared parent task
- **THEN** the guard SHALL return a blocked result
- **AND** SHALL include the conflicting task IDs and overlapping files in the report

### Requirement: Auditable Spawn Agent Guard Reports

The system SHALL persist audit artifacts for each `spawn_agent` guard evaluation.

#### Scenario: Guard writes latest and history records
- **WHEN** a `spawn_agent` guard check runs
- **THEN** the system SHALL write a latest JSON report and append a JSONL history record
- **AND** each record SHALL include actor, parent task, declared write set, allow/block result, and violations

### Requirement: Automatic Agent Tool Preflight Hook

The system SHALL run the same `spawnAgentGuard` policy automatically before the Claude Code `Agent` tool executes an internal delegation.

#### Scenario: Installed hook auto-runs guard before delegation
- **WHEN** project hooks are installed
- **AND** Claude Code is about to execute an `Agent` tool call
- **THEN** the `PreToolUse` hook SHALL derive delegation context from tool input and local Codex runtime files
- **AND** SHALL execute the same `spawn_agent` guard policy before the tool call proceeds

#### Scenario: Guard denial blocks the Agent tool call
- **WHEN** automatic preflight finds a `spawn_agent` delegation that violates `spawnAgentGuard`
- **THEN** the hook SHALL deny the `Agent` tool invocation
- **AND** SHALL return the violated rules to the Claude Code runtime as the denial reason
