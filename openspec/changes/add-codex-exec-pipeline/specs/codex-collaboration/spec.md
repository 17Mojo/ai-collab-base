## ADDED Requirements

### Requirement: Single-command Codex pipeline

The system SHALL provide a single CLI command that executes Codex collaboration pipeline end-to-end in one invocation.

#### Scenario: Pipeline success

- **WHEN** user executes `codex exec` with valid goal/steps and Codex command succeeds
- **THEN** the system runs planning, progress generation, Codex execution, and state sync in order
- **AND** the command returns success status code `0`

#### Scenario: Pipeline execution failure

- **WHEN** user executes `codex exec` and Codex execution returns non-zero
- **THEN** the system still performs state sync with latest progress/runtime
- **AND** the command returns non-zero status code

### Requirement: Argument compatibility

The system MUST keep existing codex command-line options reusable in `codex exec`.

#### Scenario: Reuse existing options

- **WHEN** user passes options such as `--intent`, `--model`, `--step`, `--steps-file`, `--max-timeout`, `--task-id`
- **THEN** the pipeline command reuses those options without introducing incompatible parameter names
