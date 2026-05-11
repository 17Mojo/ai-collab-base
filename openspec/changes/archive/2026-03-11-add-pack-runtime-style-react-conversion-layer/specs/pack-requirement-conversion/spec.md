# pack-requirement-conversion Specification

## Purpose
定义从 Owner 自然语言需求到 Pack 草案的 ReAct 转换流程，保证跨行业复用、可审计和可校验。

## ADDED Requirements

### Requirement: ReAct Conversion Pipeline
The system SHALL implement a fixed ReAct conversion pipeline for pack requirement transformation.

#### Scenario: Owner requirement enters conversion
- **WHEN** an Owner requirement form is submitted
- **THEN** pipeline SHALL execute ordered stages: Reason -> Act -> Observe (iterative)
- **AND** SHALL produce a conversion trace for audit

### Requirement: Standard Conversion Artifacts
The system SHALL output standard artifacts for every conversion run.

#### Scenario: Conversion run completes successfully
- **WHEN** conversion pipeline finishes
- **THEN** system SHALL generate `draft_pack.json`
- **AND** SHALL generate `change_manifest.md` describing inherited/new/removed elements
- **AND** SHALL generate `validation_report.md` with structure and compliance checks

### Requirement: Cross-Pack Element Reuse and Conflict Detection
The system SHALL support element reuse across existing packs and detect conflicts before publishing.

#### Scenario: Requirement requests inheritance from multiple packs
- **WHEN** converter composes elements from multiple source packs
- **THEN** system SHALL detect naming/semantic/compliance conflicts
- **AND** SHALL require explicit conflict resolution in change manifest

### Requirement: Schema and Compliance Dual Gates
The system SHALL enforce schema and compliance dual gates before draft can be marked releasable.

#### Scenario: Draft passes structure and business constraints
- **WHEN** `PromptPackV2.from_dict` and `validate()` pass
- **AND** compliance rules and industry guard checks pass
- **THEN** draft status SHALL be `ready_for_owner_review`

#### Scenario: Draft fails any required gate
- **WHEN** schema or compliance gate fails
- **THEN** draft status SHALL be `blocked`
- **AND** validation report SHALL include actionable failure reasons
