## ADDED Requirements

### Requirement: Automation Benefit Daily Aggregation
The system SHALL aggregate dispatch and receipt history into daily automation benefit metrics.

#### Scenario: Daily metrics are computed from history snapshots
- **WHEN** operator runs benefit dashboard command
- **THEN** the system SHALL read dispatch/receipt history snapshots
- **AND** aggregate per-day task volume, automation touchpoints, and efficiency ratio

### Requirement: Target Gate Tracking
The system SHALL evaluate whether the daily efficiency ratio meets target threshold.

#### Scenario: Ratio meets target
- **WHEN** daily efficiency ratio is greater than or equal to configured target
- **THEN** dashboard SHALL mark the day as target achieved

#### Scenario: Ratio does not meet target
- **WHEN** daily efficiency ratio is below configured target
- **THEN** dashboard SHALL mark the day as target not achieved

### Requirement: Benefit Dashboard Outputs
The system SHALL produce machine-readable and human-readable outputs for tracking.

#### Scenario: Markdown and JSON outputs are generated
- **WHEN** benefit dashboard command runs successfully
- **THEN** it SHALL write:
  - a JSON report with daily metrics and overall summary
  - a markdown dashboard with trend and target status
