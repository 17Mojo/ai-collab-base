## ADDED Requirements
### Requirement: Terminal Result Consistency Audit
The system SHALL audit terminal task states against their result artifacts to detect state/report divergence before closeout summaries or operator reviews rely on them.

#### Scenario: Terminal task matches result header state
- **WHEN** a task is in a terminal state and its `result_file` exists
- **AND** the result artifact declares a matching terminal status header
- **THEN** the audit SHALL mark the task as consistent
- **AND** SHALL include the task in the success count only

#### Scenario: Terminal task mismatches result header state
- **WHEN** a task is in a terminal state and its `result_file` declares a different terminal status header
- **THEN** the audit SHALL record a mismatch entry with `task_id`, state status, result-header status, and artifact path
- **AND** SHALL return a non-zero exit code when strict mode is enabled

#### Scenario: Result header status is missing or unreadable
- **WHEN** a terminal task has a readable `result_file` but no parseable top-level status header
- **THEN** the audit SHALL record the task as unparseable
- **AND** SHALL include remediation guidance to normalize the result report header

#### Scenario: Takeover task keeps original ai_type
- **WHEN** a task has a valid owner lock from `tasks takeover`
- **AND** `ai_type` and `assignee` differ because the current owner completed the task after takeover
- **THEN** the audit SHALL NOT treat that ownership split as a mismatch by itself
- **AND** SHALL continue to audit only the terminal state versus result-header status

#### Scenario: Strict contract validation includes result consistency audit
- **WHEN** an operator runs `python3 -m ai_collab.cli tasks validate-contract --strict`
- **THEN** the system SHALL run contract validation first
- **AND** SHALL run terminal result consistency audit in the same invocation
- **AND** SHALL return a non-zero exit code if either contract validation fails or result consistency issues are detected
