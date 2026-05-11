## ADDED Requirements

### Requirement: Governance Role Source of Truth
The system SHALL maintain one authoritative role mapping for active agents, leadership, and disabled agents across governance documents and runtime configuration.

#### Scenario: Runtime config and governance docs are aligned
- **WHEN** governance change `update-agent-governance-handover` is approved
- **THEN** `.vscode/ai-collab.json` and governance docs SHALL reflect the same active/disabled agent set
- **AND** conflicting legacy role statements SHALL be marked deprecated or updated

### Requirement: Codex Technical Partner Leadership
The system SHALL designate Codex as the default technical-partner lead for global planning, task orchestration, and quality gating after governance handover takes effect.

#### Scenario: New task requires global planning
- **WHEN** a cross-module or multi-phase task is initiated after effective date
- **THEN** Codex SHALL produce the planning baseline and execution split
- **AND** user decisions SHALL remain final authority for product direction

### Requirement: Claude Execution Ownership
The system SHALL assign Claude Code as primary execution owner for implementation batches unless explicitly overridden by approved governance rules.

#### Scenario: Implementation batch is dispatched
- **WHEN** a task batch enters implementation status
- **THEN** Claude Code SHALL be assigned as executor by default
- **AND** handoff notes SHALL include files, tests, and completion evidence

### Requirement: CodeArts Copilot Replacement Without Leadership
The system SHALL assign CodeArts to replace Copilot execution-assistant duties while preventing CodeArts from technical-partner leadership responsibilities.

#### Scenario: Task routing after governance switch
- **WHEN** new implementation/testing/documentation tasks are created
- **THEN** CodeArts MAY be assigned as execution support
- **AND** CodeArts SHALL NOT be assigned as global planning/orchestration lead

### Requirement: Transition Guardrail
The system SHALL enforce existing governance rules before the new governance change is approved and marked effective.

#### Scenario: Change is drafted but not approved
- **WHEN** governance update is still pending approval
- **THEN** agents SHALL continue operating under existing rules and protocols
- **AND** no irreversible governance switch SHALL be applied
