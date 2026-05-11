# prompt-pack-runtime-style Specification

## Purpose
定义 Prompt Pack 执行期风格微调能力，确保 Operator 可进行运行时调优，同时保证基线 Pack JSON 不被污染。

## ADDED Requirements

### Requirement: Runtime Override Contract
The system SHALL support runtime style overrides via `executePack` message payload.

#### Scenario: Execute request carries runtime overrides
- **WHEN** Popup triggers `executePack`
- **THEN** request payload SHALL include `data.runtime_overrides`
- **AND** runtime overrides SHALL be forwarded to content executor without dropping keys

### Requirement: Override Whitelist and Validation
The system SHALL validate runtime override keys and values against a whitelist.

#### Scenario: Valid override parameters are accepted
- **WHEN** override keys are in whitelist and values are in allowed range/enums
- **THEN** executor SHALL apply overrides to execution context
- **AND** execution SHALL continue normally

#### Scenario: Invalid override parameters are rejected safely
- **WHEN** override keys/values are invalid
- **THEN** system SHALL ignore invalid entries and fallback to defaults
- **AND** SHALL log validation warnings for audit

### Requirement: Baseline Pack Immutability
The system SHALL NOT persist runtime override changes into baseline Pack JSON.

#### Scenario: Operator adjusts style during execution
- **WHEN** runtime overrides are applied
- **THEN** only execution-time effective config SHALL change
- **AND** stored Pack metadata/workflow SHALL remain unchanged

### Requirement: Backward Compatibility for Existing Flow
The system SHALL remain compatible with execute requests that do not provide overrides.

#### Scenario: Legacy executePack request without runtime_overrides
- **WHEN** request payload only contains `input`
- **THEN** executor SHALL run with default style settings
- **AND** behavior SHALL match pre-change baseline
