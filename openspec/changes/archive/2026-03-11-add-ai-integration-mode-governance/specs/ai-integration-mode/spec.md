# ai-integration-mode Specification

## Purpose
定义 AI 集成模块的 Mock/Fallback/Real 三种模式治理规范，确保模拟响应可识别、可配置、可回退，并提供清晰的迁移路径。

## ADDED Requirements

### Requirement: Integration Mode Definition
The system SHALL define three distinct integration modes for AI integration modules.

#### Scenario: Three modes are clearly defined
- **WHEN** an AI integration module is configured
- **THEN** it SHALL support one of three modes:
  - `mock`: 仅模拟模式（测试用，强制使用模拟响应）
  - `fallback`: 优先真实，失败回退模拟（生产默认）
  - `real`: 仅真实模式（生产用，无模拟回退）
- **AND** the mode SHALL be queryable via `get_mode(module_name)`

#### Scenario: Default mode is fallback for safety
- **WHEN** a module is not explicitly configured
- **THEN** it SHALL default to `fallback` mode
- **AND** SHALL log a warning if real integration is unavailable

### Requirement: Mock Response Transparency
The system SHALL mark all mock responses with explicit metadata.

#### Scenario: Mock responses contain identifying metadata
- **WHEN** an integration module returns a mock response
- **THEN** the response SHALL include `_mock: True`
- **AND** SHALL include `_mock_reason` explaining why mock was used
- **AND** SHALL include timestamp for audit trail

#### Scenario: Mock responses trigger warnings
- **WHEN** a mock response is generated in non-test environment
- **THEN** the system SHALL log a warning with module name and reason
- **AND** the warning SHALL include instructions to enable real integration

### Requirement: Environment Variable Override
The system SHALL support environment variable configuration for deployment flexibility.

#### Scenario: AI_INTEGRATION_MODE overrides defaults
- **WHEN** `AI_INTEGRATION_MODE` environment variable is set
- **THEN** all modules SHALL respect this global setting
- **AND** per-module defaults SHALL be overridden only if explicitly set
- **AND** invalid mode values SHALL be rejected with clear error

#### Scenario: Per-module override is supported
- **WHEN** `AI_INTEGRATION_MODE_<MODULE>=<mode>` is set
- **THEN** only that specific module SHALL use the configured mode
- **AND** other modules SHALL use their defaults or global setting

### Requirement: Mode Query and Validation
The system SHALL provide utilities to query and validate integration modes.

#### Scenario: Query current mode for a module
- **WHEN** `get_mode(module_name)` is called
- **THEN** it SHALL return the configured IntegrationMode enum
- **AND** it SHALL respect environment variable overrides
- **AND** it SHALL raise ValueError for invalid module names

#### Scenario: Check if module is in mock mode
- **WHEN** `is_mock_mode(module_name)` is called
- **THEN** it SHALL return True if mode is `mock`
- **AND** SHALL return False for `fallback` or `real` modes

#### Scenario: Check if fallback is allowed
- **WHEN** `should_use_fallback(module_name)` is called
- **THEN** it SHALL return True for `mock` or `fallback` modes
- **AND** SHALL return False for `real` mode

### Requirement: Health Check and Monitoring
The system SHALL provide health check endpoints for integration monitoring.

#### Scenario: Query all module modes
- **WHEN** health check endpoint is called
- **THEN** it SHALL return current mode for all configured modules
- **AND** SHALL indicate which modules are using mock responses
- **AND** SHALL include last mock fallback timestamp if available

#### Scenario: Module-specific health check
- **WHEN** health check is called for a specific module
- **THEN** it SHALL return mode and integration status
- **AND** SHALL list any recent mock fallbacks with reasons
- **AND** SHALL include configuration source (default/env/per-module)
