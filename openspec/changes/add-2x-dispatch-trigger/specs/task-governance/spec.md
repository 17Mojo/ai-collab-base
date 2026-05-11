## ADDED Requirements

### Requirement: Trigger Phrase Dispatch
The system SHALL support trigger phrase based dispatch kickoff for operator-friendly handoff.

#### Scenario: 2X phrase triggers dispatch flow
- **WHEN** operator runs CLI trigger command with a valid phrase such as `2X DISPATCH`
- **THEN** the system SHALL invoke dispatch bridge flow
- **AND** generate the latest dispatch orders markdown

#### Scenario: Shortcut command maps to trigger phrase
- **WHEN** operator runs shortcut command `2x claude`, `2x codearts`, or `2x all`
- **THEN** the system SHALL map it to canonical trigger phrase flow
- **AND** preserve the same dispatch/audit behavior as `trigger`

#### Scenario: 2x all falls back to receipt when dispatch queue is empty
- **WHEN** operator runs `2x all` and there are no `planning/pending` tasks but existing `testing` tasks
- **THEN** the system SHALL execute receipt flow instead of dispatch flow
- **AND** preserve receipt audit behavior

### Requirement: Agent-Scoped Handoff Payload Generation
The system SHALL generate agent-scoped handoff payload files from dispatch orders to reduce copy/paste mistakes.

#### Scenario: Claude and CodeArts payloads are generated
- **WHEN** trigger flow succeeds
- **THEN** the system SHALL write dedicated payload files for `claude_code` and `codearts_agent`
- **AND** each payload SHALL include source orders reference and task instructions for that assignee

#### Scenario: Single-target output is supported
- **WHEN** operator specifies a trigger target agent
- **THEN** the system SHALL generate payload for that target only

### Requirement: Trigger Audit Trail
The system SHALL persist trigger report and history for traceability.

#### Scenario: Trigger run is recorded
- **WHEN** trigger command finishes
- **THEN** it SHALL write a JSON report with phrase, target, and output files
- **AND** append a JSONL history snapshot
