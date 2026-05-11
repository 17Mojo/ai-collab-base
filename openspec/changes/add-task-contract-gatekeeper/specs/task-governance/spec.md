## ADDED Requirements

### Requirement: Task Contract Required Fields
The system SHALL enforce required task metadata fields for newly created execution tickets.

#### Scenario: New task misses required fields
- **WHEN** a task is created or validated without one of required fields (`change_id`, `primary_skill`, `support_skills`, `acceptance_commands`, `result_file`)
- **THEN** validation SHALL fail with explicit missing-field details
- **AND** task status SHALL NOT advance to implementing

### Requirement: Contract Validation Entry
The system SHALL provide an executable validation entry for task contract checking in local workflow and controller runs.

#### Scenario: Controller preflight check
- **WHEN** operator runs controller preflight or one-shot dry run
- **THEN** task contract validation result SHALL be included in report output
- **AND** failures SHALL include task identifiers and remediation hints

### Requirement: Legacy Task Compatibility
The system SHALL support legacy historical tasks without blocking current execution.

#### Scenario: Historical task archive scan
- **WHEN** validator scans cancelled/completed historical tasks created before guardrail effective date
- **THEN** validator MAY report warnings
- **AND** validator SHALL NOT block current active pipeline due to historical-only records
