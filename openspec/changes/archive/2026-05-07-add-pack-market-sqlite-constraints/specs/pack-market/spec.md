## ADDED Requirements

### Requirement: SQLite CHECK Constraint for Feedback Type

The system SHALL enforce feedback_type enumeration at SQLite database level using CHECK constraint.

#### Scenario: Database rejects invalid feedback_type

- **WHEN** direct SQL insert attempts to add feedback with type not in ('bug', 'suggestion', 'request')
- **THEN** SQLite SHALL raise IntegrityError
- **AND** SHALL prevent invalid data from being stored

#### Scenario: Database accepts valid feedback_type

- **WHEN** direct SQL insert adds feedback with type in ('bug', 'suggestion', 'request')
- **THEN** SQLite SHALL accept the insert
- **AND** SHALL store feedback successfully

#### Scenario: Python and SQLite dual-layer validation

- **WHEN** feedback is submitted through normal API path
- **THEN** Python dataclass SHALL first validate feedback_type in `__post_init__`
- **AND** SQLite SHALL provide secondary CHECK constraint validation
- **AND** both layers SHALL enforce same enumeration values

### Requirement: SQLite CHECK Constraint for Rating Range

The system SHALL enforce rating range (1-5) at SQLite database level using CHECK constraint.

#### Scenario: Database rejects rating out of range

- **WHEN** direct SQL insert attempts to add rating outside 1-5 range
- **THEN** SQLite SHALL raise IntegrityError
- **AND** SHALL prevent invalid rating from being stored

#### Scenario: Database accepts valid rating

- **WHEN** direct SQL insert adds rating between 1 and 5
- **THEN** SQLite SHALL accept the insert
- **AND** SHALL store rating successfully

#### Scenario: Rating boundary values accepted

- **WHEN** rating is exactly 1 or exactly 5
- **THEN** SQLite SHALL accept both boundary values
- **AND** SHALL store rating successfully