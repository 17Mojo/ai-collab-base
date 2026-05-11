## ADDED Requirements

### Requirement: Receipt Candidate Detection
The system SHALL detect auto-receipt candidates from task contracts for tasks ready to be closed.

#### Scenario: Testing tasks are detected for receipt
- **WHEN** operator runs receipt bridge
- **THEN** tasks in `testing` status SHALL be collected as receipt candidates
- **AND** each candidate SHALL include `task_id`, `assignee`, and `result_file`

#### Scenario: Tasks requiring follow-up are skipped
- **WHEN** task has `conclusion=action_required` or `review_conclusion=action_required`
- **THEN** receipt bridge SHALL skip automatic completion for that task

### Requirement: Auto Completion with Evidence Gate
The system SHALL auto-complete only tasks that pass the existing completion evidence gate.

#### Scenario: Eligible task is auto-completed
- **WHEN** task is in `testing` and result artifact passes completion gate
- **THEN** receipt bridge SHALL update task status to `completed`
- **AND** task SHALL be removed from active list and appended to completed list

#### Scenario: Invalid result artifact blocks completion
- **WHEN** result file is missing or required sections are incomplete
- **THEN** receipt bridge SHALL keep the task in `testing`
- **AND** report SHALL capture the gate error reason

### Requirement: Receipt Audit Trail
The system SHALL persist receipt state and history for deduplication and traceability.

#### Scenario: Duplicate receipt is prevented
- **WHEN** a task has already been received and reclose is not enabled
- **THEN** receipt bridge SHALL skip repeated completion for that task
- **AND** report SHALL include the task in `already_received_tasks`

#### Scenario: Receipt report and summary are persisted
- **WHEN** receipt bridge runs
- **THEN** it SHALL write:
  - a JSON report with candidate/completed/error counts
  - a JSONL history snapshot
  - a markdown summary file for operator review
