## ADDED Requirements

### Requirement: Explicit ACK Evidence Gate for Claude Closeout
The system SHALL require explicit ACK evidence before a `claude_code` task is considered eligible for governance closeout.

#### Scenario: CLI ACK persists explicit evidence for Claude
- **WHEN** operator runs `python3 -m ai_collab.cli ack --task-id <id> --ai claude_code --status ok`
- **THEN** the system SHALL print a one-line `C.ACK|...` protocol message
- **AND** SHALL persist ACK bridge evidence whose source is marked as explicit (`cli-ack`)

#### Scenario: Auto-close paths skip Claude task without explicit ACK
- **WHEN** `receipt`, `reconcile_state_drift`, or `missing_ack_monitor` evaluates a `claude_code` task
- **AND** no ACK bridge item exists whose source starts with `cli-ack` or `chat-ack`
- **THEN** the system SHALL NOT auto-complete or auto-bridge that task
- **AND** SHALL report the task as blocked by explicit ACK requirement

#### Scenario: Stop hook blocks session end for unresolved Claude closeout
- **WHEN** a `claude_code` task is in `testing` or `completed`
- **AND** result evidence exists but explicit ACK evidence is missing
- **THEN** Stop Hook SHALL block session end
- **AND** SHALL print the exact `python3 -m ai_collab.cli ack --task-id <id> --ai claude_code --status ok` command

### Requirement: Explicit ACK Audit Visibility
The system SHALL distinguish legacy non-explicit Claude ACK bridge records from valid explicit ACK evidence.

#### Scenario: Legacy fallback bridge is surfaced as stale evidence
- **WHEN** monitoring or reporting inspects ACK bridge state
- **AND** a `claude_code` bridge item has a non-explicit source such as `missing_ack_monitor*` or other fallback source
- **THEN** the system SHALL surface that item as skipped or stale explicit-ACK-required evidence
- **AND** SHALL NOT treat it as valid closeout evidence for Claude automation

#### Scenario: Explicit ACK automatically clears legacy remediation residue
- **WHEN** a previously flagged legacy `claude_code` fallback bridge later receives `cli-ack` or `chat-ack` evidence
- **THEN** the system SHALL replace the legacy bridge source with the explicit ACK source
- **AND** SHALL clear the active remediation residue marker for that task
- **AND** SHALL stop reporting that task as stale explicit-ACK-required evidence
