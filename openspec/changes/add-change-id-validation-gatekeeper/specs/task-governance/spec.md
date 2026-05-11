## ADDED Requirements

### Requirement: Change ID Must Resolve to Governed Source
The system SHALL validate task `change_id` against governed sources before considering task contract valid.

#### Scenario: Validate task with OpenSpec-backed change
- **WHEN** task contract contains `change_id` as a normal OpenSpec change identifier
- **THEN** validator SHALL confirm the change exists under `openspec/changes` or archived changes
- **AND** task contract SHALL fail if change directory does not exist

#### Scenario: Validate task with governance whitelist label
- **WHEN** task contract contains `change_id` as `bugfix/no-spec` or `legacy/task-contract-migration`
- **THEN** validator SHALL treat the `change_id` as valid
- **AND** task contract SHALL continue to validate remaining required fields
