## ADDED Requirements

### Requirement: Formal Session Registry
The system SHALL maintain a formal registry for Codex, Claude Code, and CodeArts execution sessions instead of relying only on implicit workspace context.

#### Scenario: Session is registered for an external assignee
- **WHEN** an operator or automation registers a session for `claude_code`, `codearts_agent`, or `codex`
- **THEN** the system SHALL persist a session record containing at least `session_id`, `assignee`, `transport_mode`, `session_status`, `last_seen_at`, and `last_handoff_artifact`
- **AND** SHALL make that record available to monitoring and intervention workflows

#### Scenario: Missing session registration is surfaced explicitly
- **WHEN** a task or trigger target has no active registered session
- **THEN** the system SHALL classify the session state as `unregistered` or equivalent
- **AND** SHALL NOT imply that the target session can receive automatic intervention

### Requirement: Session Health Aggregation
The system SHALL aggregate existing governance signals into a session health model that can detect drift, silence, and protocol anomalies.

#### Scenario: Existing control-plane anomaly degrades session health
- **WHEN** payload freshness fails, ACK watchdog times out, explicit ACK remains missing, or terminal result consistency detects divergence
- **THEN** the system SHALL attach the anomaly to the affected session
- **AND** SHALL record a machine-readable `reason_code` and health status transition

#### Scenario: Repeated silence after RUN is recorded as a session incident
- **WHEN** a registered session does not return the expected ACK within the configured response window after `C.RUN`, `A.RUN`, or `X.RUN`
- **THEN** the system SHALL record a session incident for that assignee
- **AND** SHALL include the recommended remediation path in the health record

### Requirement: Intervention Artifact and Delivery Tracking
The system SHALL represent session corrections as first-class intervention records with explicit delivery state.

#### Scenario: Manual-only transport generates a pending intervention artifact
- **WHEN** a session incident requires correction
- **AND** the target session transport mode is `manual` or no bridge is configured
- **THEN** the system SHALL generate a concrete intervention artifact containing the exact corrective message and destination session
- **AND** SHALL mark the intervention as `pending_operator_delivery` or equivalent

#### Scenario: Bridge transport allows automated delivery
- **WHEN** a session incident requires correction
- **AND** the target session has an enabled and auditable bridge transport
- **THEN** the system SHALL queue or deliver the intervention through that transport
- **AND** SHALL persist the resulting delivery status and timestamp

### Requirement: Honest Automation Boundary
The system MUST minimize human glue work without overstating control over external sessions.

#### Scenario: System reports operator assist only when transport is unavailable
- **WHEN** no supported transport exists for the affected external session
- **THEN** the system SHALL request only the minimal operator forwarding step needed to deliver the generated intervention artifact
- **AND** SHALL identify that need as a transport limitation rather than a missing governance decision

#### Scenario: System does not claim synchronization it cannot prove
- **WHEN** an intervention has been generated but not delivered through a verified bridge transport
- **THEN** the system SHALL NOT mark the session as synchronized or auto-corrected
- **AND** SHALL continue surfacing the intervention as pending until delivery or resolution is recorded
