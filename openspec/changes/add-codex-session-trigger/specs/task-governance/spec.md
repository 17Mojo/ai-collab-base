## ADDED Requirements

### Requirement: Codex Session Trigger Parity
The system SHALL provide a formal Codex session trigger that is symmetric with Claude and CodeArts session triggers.

#### Scenario: Operator triggers Codex session with X.RUN
- **WHEN** operator sends `X.RUN` in the Codex session
- **THEN** Codex SHALL treat it as the canonical execution kickoff for Codex-assigned work in the current round
- **AND** SHALL use the latest Codex handoff payload as the execution reference

#### Scenario: Codex session returns noop consistently
- **WHEN** operator sends `X.RUN`
- **AND** there is no active Codex-assigned task to execute
- **THEN** Codex SHALL respond with `X.ACK|task=none|status=noop|result=none`

### Requirement: Codex Trigger Payload Generation
The system SHALL generate Codex-scoped trigger payloads alongside other agent payloads when Codex is a trigger target.

#### Scenario: Trigger flow generates Codex payload
- **WHEN** operator runs `trigger --phrase "2X DISPATCH CODEX"` or `2x codex`
- **THEN** the system SHALL write `collaboration/monitoring/AGENT_TRIGGER_codex_latest.md`
- **AND** SHALL record the generated file in trigger report/history output

#### Scenario: All-target trigger includes Codex payload
- **WHEN** operator runs an all-target trigger flow that includes Codex in enabled agents
- **THEN** the system SHALL generate Codex payload together with Claude and CodeArts payloads

### Requirement: Codex Trigger Safety Alignment
The system SHALL apply the same freshness and audit guardrails to Codex session triggers as to other session triggers.

#### Scenario: Codex trigger requires freshness validation
- **WHEN** Codex receives `X.RUN`
- **THEN** execution instructions SHALL require freshness validation before task execution
- **AND** SHALL provide the same repair path used by other agent payloads

#### Scenario: Codex trigger is auditable
- **WHEN** Codex-targeted trigger flow completes
- **THEN** the system SHALL preserve report/history records with Codex target metadata
- **AND** SHALL keep Codex trigger behavior traceable in the same audit trail as other agents
