## ADDED Requirements

### Requirement: Historical Task Contract Migration Command
The system SHALL provide an executable command to migrate historical tasks to the full task-contract schema.

#### Scenario: Run migration for all tasks
- **WHEN** operator runs `python3 -m ai_collab.cli tasks migrate-contract --scope all`
- **THEN** system SHALL backfill missing required fields (`change_id`, `assignee`, `reviewer`, `primary_skill`, `support_skills`, `acceptance_commands`, `result_file`)
- **AND** system SHALL set `contract_required=true` for migrated tasks
- **AND** command output SHALL include `migrated_count`, `remaining_legacy`, and invalid task details (if any)

#### Scenario: Dry-run migration
- **WHEN** operator runs `python3 -m ai_collab.cli tasks migrate-contract --scope all --dry-run`
- **THEN** system SHALL output migration statistics without persisting task changes
- **AND** operator SHALL be able to decide whether to execute the actual migration

## MODIFIED Requirements

### Requirement: Legacy Task Compatibility
The system SHALL eliminate legacy-skip behavior in contract validation after migration capability is available.

#### Scenario: Validate contracts after migration
- **WHEN** operator runs `python3 -m ai_collab.cli tasks validate-contract --scope all`
- **THEN** validator SHALL check all tasks in scope instead of skipping legacy tasks
- **AND** `skipped_tasks` SHALL remain `0` under the unified validation path
