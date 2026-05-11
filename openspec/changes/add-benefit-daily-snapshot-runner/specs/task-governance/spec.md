## ADDED Requirements

### Requirement: Daily Benefit Snapshot Persistence
The system SHALL generate and persist a daily automation benefit snapshot.

#### Scenario: Daily snapshot writes latest and dated reports
- **WHEN** operator runs daily benefit snapshot runner
- **THEN** the system SHALL write the latest benefit report/dashboard
- **AND** write a dated report snapshot for the current date

### Requirement: Daily Benefit History Tracking
The system SHALL append a daily summary record for longitudinal tracking.

#### Scenario: Daily history is appended on apply mode
- **WHEN** daily snapshot runner completes in apply mode
- **THEN** it SHALL append one JSON line with date, ratio, and target status to daily history

### Requirement: Dry-Run Safety
The system SHALL support dry-run mode without mutating files.

#### Scenario: Dry-run computes without writes
- **WHEN** runner is executed with `--dry-run`
- **THEN** it SHALL print computed summary
- **AND** SHALL NOT write latest report, dated report, dashboard, or daily history
