## ADDED Requirements

### Requirement: Dispatch Candidate Detection
The system SHALL detect dispatch candidates from task contracts for tasks waiting to be executed.

#### Scenario: Planning tasks are detected for dispatch
- **WHEN** operator runs dispatch bridge in default mode
- **THEN** tasks in `planning` status SHALL be collected as dispatch candidates
- **AND** each candidate SHALL include `task_id`, `assignee`, `result_file`, and `acceptance_commands`

#### Scenario: Pending tasks can be included explicitly
- **WHEN** operator enables include-pending mode
- **THEN** tasks in `pending` status SHALL also be collected as dispatch candidates

### Requirement: Dispatch Order Bundle Generation
The system SHALL generate a ready-to-send dispatch order bundle grouped by assignee.

#### Scenario: Orders are generated for Claude and CodeArts
- **WHEN** dispatch candidates exist for `claude_code` or `codearts_agent`
- **THEN** output markdown SHALL include per-task executable instructions:
  - status update to `implementing`
  - acceptance command execution
  - result file requirement
  - status update to `testing`

### Requirement: Dispatch Audit Trail
The system SHALL persist dispatch state and history for deduplication and traceability.

#### Scenario: Duplicate dispatch is prevented
- **WHEN** a task has already been dispatched and redispatch is not enabled
- **THEN** dispatch bridge SHALL skip re-dispatch for that task
- **AND** report SHALL include the skipped task in `already_dispatched_tasks`

#### Scenario: Dispatch report and history are persisted
- **WHEN** dispatch bridge runs
- **THEN** it SHALL write:
  - a JSON report with candidate/dispatched counts
  - a JSONL history snapshot
  - a markdown dispatch order file
