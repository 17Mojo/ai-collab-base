## ADDED Requirements

### Requirement: Pack Listing and Discovery
The system SHALL provide pack listing with category, rating, and search capabilities.

#### Scenario: User searches packs by keyword
- **WHEN** user submits a search query
- **THEN** system SHALL return matching packs sorted by relevance
- **AND** SHALL include rating and download count in results

#### Scenario: User filters packs by category
- **WHEN** user selects a category filter
- **THEN** system SHALL return packs belonging to that category
- **AND** SHALL maintain existing sort order

#### Scenario: User views pack details
- **WHEN** user requests pack by pack_id
- **THEN** system SHALL return full pack listing with all metadata
- **AND** SHALL include aggregate rating and feedback count

### Requirement: Pack Rating System
The system SHALL support pack rating with 1-5 scale and validation.

#### Scenario: User submits valid rating
- **WHEN** user submits rating between 1 and 5
- **THEN** system SHALL store the rating
- **AND** SHALL update pack average rating

#### Scenario: User submits invalid rating
- **WHEN** user submits rating outside 1-5 range
- **THEN** system SHALL reject the rating
- **AND** SHALL return validation error

#### Scenario: User submits duplicate rating
- **WHEN** user attempts to rate same pack multiple times
- **THEN** system SHALL update existing rating instead of creating new
- **AND** SHALL preserve created_at timestamp

### Requirement: User Feedback Collection
The system SHALL collect user feedback with type classification.

#### Scenario: User submits bug feedback
- **WHEN** user submits feedback with type "bug"
- **THEN** system SHALL store feedback with created_at timestamp
- **AND** SHALL mark feedback as pending review

#### Scenario: User submits feature request
- **WHEN** user submits feedback with type "request"
- **THEN** system SHALL store feedback
- **AND** SHALL link to pack_id for tracking

#### Scenario: User submits suggestion
- **WHEN** user submits feedback with type "suggestion"
- **THEN** system SHALL store feedback
- **AND** SHALL mark for moderation review

### Requirement: Pack Status Lifecycle Integration
The system SHALL manage pack status through DRAFT/PENDING/APPROVED/REJECTED/ARCHIVED states aligned with prompt-pack-lifecycle.

#### Scenario: Pack enters pending review
- **WHEN** pack author submits pack for review
- **THEN** system SHALL set status to PENDING
- **AND** SHALL notify reviewers

#### Scenario: Pack is approved
- **WHEN** reviewer approves pending pack
- **THEN** system SHALL set status to APPROVED
- **AND** SHALL make pack visible in market

#### Scenario: Pack is rejected
- **WHEN** reviewer rejects pending pack
- **THEN** system SHALL set status to REJECTED
- **AND** SHALL provide rejection reason to author

#### Scenario: Pack is archived
- **WHEN** pack author or admin requests archive
- **THEN** system SHALL set status to ARCHIVED
- **AND** SHALL remove from active market listings

### Requirement: Pack Baseline Immutability
The system SHALL NOT modify pack baseline fields when storing ratings or feedback.

#### Scenario: Rating updates aggregate only
- **WHEN** rating is submitted for a pack
- **THEN** system SHALL update rating and rating_count aggregate fields only
- **AND** SHALL NOT modify pack_name, description, author, or workflow fields

#### Scenario: Feedback stored separately
- **WHEN** feedback is submitted for a pack
- **THEN** system SHALL store in user_feedbacks table
- **AND** SHALL NOT modify pack listing baseline fields
