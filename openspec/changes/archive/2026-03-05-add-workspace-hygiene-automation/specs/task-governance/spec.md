## ADDED Requirements

### Requirement: Periodic Workspace Hygiene Loop
The system SHALL support a configurable periodic workspace hygiene loop to reduce workspace and staging accumulation.

#### Scenario: Poll loop runs on configured interval
- **WHEN** `workspaceHygiene.enabled` is true and scheduler interval is reached
- **THEN** the system SHALL execute hygiene flow in configured domain order
- **AND** SHALL persist a hygiene report snapshot

### Requirement: Receipt-Triggered Immediate Hygiene
The system SHALL trigger an immediate hygiene run after successful receipt closure when configured.

#### Scenario: Receipt closes tasks and triggers hygiene
- **WHEN** receipt command completes with `completed_count > 0`
- **AND** `workspaceHygiene.onReceiptClose` is true
- **THEN** the system SHALL run one hygiene cycle immediately
- **AND** SHALL record trigger source as `post-receipt`

### Requirement: Safe Domain Chain Automation
The system SHALL automate domain staging in an explicit ordered chain with preview-before-apply behavior.

#### Scenario: Stage chain executes ops -> docs -> other by default
- **WHEN** hygiene runs with default domain order
- **THEN** it SHALL preview candidate files per domain before apply
- **AND** it SHALL apply staging only for domains with candidate files

#### Scenario: Source domain requires explicit enablement
- **WHEN** source domain is not explicitly enabled
- **THEN** hygiene SHALL NOT stage source files automatically

### Requirement: Reversible Audit Snapshot
The system SHALL persist reversible audit snapshots for each hygiene run.

#### Scenario: Hygiene snapshot is written for audit and rollback analysis
- **WHEN** hygiene run starts and finishes
- **THEN** the system SHALL write before/after counters, domain distribution, and sample paths
- **AND** SHALL append an immutable JSONL history record

### Requirement: Non-Destructive Default Behavior
The system MUST remain non-destructive by default.

#### Scenario: No automatic commit or push
- **WHEN** hygiene automation runs
- **THEN** it SHALL NOT auto-commit or auto-push
- **AND** it SHALL stop on guard violations unless explicit override is provided
