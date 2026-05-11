## ADDED Requirements

### Requirement: Lifecycle Stage Specification
The system SHALL define Prompt Pack lifecycle stages as Generation, Review, Iteration, and Archive with explicit entry/exit criteria.

#### Scenario: New Prompt Pack capability planning
- **WHEN** a new Prompt Pack capability is proposed
- **THEN** proposal SHALL identify which lifecycle stage(s) are affected
- **AND** stage-level acceptance criteria SHALL be documented before execution

### Requirement: OpenSpec-to-Task Binding
The system SHALL require execution tasks to bind to an OpenSpec `change_id` for lifecycle-impacting changes.

#### Scenario: Lifecycle change enters implementation
- **WHEN** a lifecycle-impacting change is approved
- **THEN** execution tasks SHALL include `change_id` matching the approved OpenSpec change
- **AND** result files SHALL include acceptance command evidence

### Requirement: No-Spec Exception Boundary
The system SHALL define a no-spec exception boundary for bugfix-only or non-behavioral changes.

#### Scenario: Minor fix with no lifecycle impact
- **WHEN** change only restores intended behavior without lifecycle contract modification
- **THEN** task MAY use `bugfix/no-spec`
- **AND** task SHALL still include skill fields and acceptance commands

### Requirement: Archive Readiness Evidence
The system SHALL require archive readiness evidence before lifecycle stage Archive is completed.

#### Scenario: Pack lifecycle archive decision
- **WHEN** a pack change requests archive completion
- **THEN** evidence SHALL include generation/review/iteration trace and final result file
- **AND** OpenSpec validation SHALL pass in strict mode
