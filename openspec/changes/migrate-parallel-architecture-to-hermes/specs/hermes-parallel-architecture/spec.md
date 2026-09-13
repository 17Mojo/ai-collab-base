# Spec: Hermes Parallel Architecture

## ADDED Requirements

### Requirement: Concurrent Query Execution
The system SHALL support concurrent queries to multiple LLM providers with timeout control.

#### Scenario: Query multiple models concurrently
- **WHEN** user requests insights for multiple topics
- **THEN** system SHALL execute queries concurrently using asyncio.gather
- **AND** SHALL limit concurrency to configured max_concurrent value
- **AND** SHALL enforce global timeout (default 60 seconds)

#### Scenario: Single provider timeout
- **WHEN** a single provider exceeds its timeout limit
- **THEN** system SHALL retry up to max_retries times
- **AND** SHALL isolate failure (not affect other providers)
- **AND** SHALL return partial results from successful providers

#### Scenario: Result normalization
- **WHEN** all queries complete (success or failure)
- **THEN** system SHALL normalize results to unified format
- **AND** SHALL filter out failed results
- **AND** SHALL include metadata (provider, latency, status)

---

### Requirement: Task State Management
The system SHALL manage task lifecycle through defined states with checkpoint support.

#### Scenario: Task state transition
- **WHEN** task status changes
- **THEN** system SHALL validate state transition is allowed
- **AND** SHALL persist state to storage atomically
- **AND** SHALL create checkpoint backup

#### Scenario: Concurrent state modification
- **WHEN** multiple processes modify same task
- **THEN** system SHALL detect conflicts via file lock
- **AND** SHALL merge states using last-write-wins with conflict list
- **AND** SHALL preserve conflict history for audit

#### Scenario: Heartbeat timeout detection
- **WHEN** task in implementing/testing state exceeds activeTimeoutSec
- **THEN** system SHALL auto-downgrade to blocked status
- **AND** SHALL record timeout event in task history
- **AND** SHALL notify configured recipients

---

### Requirement: Checkpoint and Recovery
The system SHALL support checkpoint backup and recovery for long-running tasks.

#### Scenario: Automatic checkpoint creation
- **WHEN** task state changes
- **THEN** system SHALL create timestamped backup file
- **AND** SHALL retain last N checkpoints (configurable)
- **AND** SHALL use atomic write to prevent corruption

#### Scenario: Task recovery from checkpoint
- **WHEN** task fails and user requests recovery
- **THEN** system SHALL load latest checkpoint
- **AND** SHALL resume from last successful stage
- **AND** SHALL skip already completed stages

---

### Requirement: Agent Notification System
The system SHALL support three notification modes for inter-agent communication.

#### Scenario: Broadcast notification
- **WHEN** system needs to notify all agents
- **THEN** system SHALL use broadcast mode
- **AND** SHALL deliver message to all active agents
- **AND** SHALL record delivery status

#### Scenario: Mention notification
- **WHEN** system needs to notify specific agents
- **THEN** system SHALL use @mention mode
- **AND** SHALL deliver message only to mentioned agents
- **AND** SHALL include mention metadata in message

#### Scenario: Direct notification
- **WHEN** system needs private communication
- **THEN** system SHALL use direct mode
- **AND** SHALL deliver message to single agent
- **AND** SHALL NOT expose to other agents

---

### Requirement: Intervention Queue
The system SHALL support human intervention queue for tasks requiring manual review.

#### Scenario: Enqueue intervention
- **WHEN** task requires human intervention
- **THEN** system SHALL create intervention record
- **AND** SHALL persist to intervention queue
- **AND** SHALL generate intervention summary (Markdown)

#### Scenario: Intervention history tracking
- **WHEN** intervention is created/resolved
- **THEN** system SHALL append to history file (JSONL format)
- **AND** SHALL include timestamp, assignee, reason, status
- **AND** SHALL support history query by task_id/date

#### Scenario: Intervention pack generation
- **WHEN** intervention is enqueued
- **THEN** system SHALL generate intervention pack (Markdown)
- **AND** SHALL include task context, reason, suggested actions
- **AND** SHALL write to packs/ directory

---

### Requirement: Task Dispatch System
The system SHALL support task dispatch with payload generation.

#### Scenario: Dispatch task to agent
- **WHEN** operator dispatches task to specific agent
- **THEN** system SHALL generate JSON payload file
- **AND** SHALL include task_id, steps, acceptance_criteria, ack_format
- **AND** SHALL register task in state manager

#### Scenario: Payload format validation
- **WHEN** payload file is generated
- **THEN** system SHALL validate JSON syntax
- **AND** SHALL verify required fields present
- **AND** SHALL write to both monitoring/ and dispatch/payloads/ locations

---

## MODIFIED Requirements

### Requirement: Report Generation Performance
The system SHALL generate reports using parallel execution.

#### Previous behavior
Sequential insight generation for each topic.

#### New behavior
- **WHEN** report generation is triggered
- **THEN** system SHALL use consensus_engine for parallel execution
- **AND** SHALL generate insights for tech/market/policy concurrently
- **AND** SHALL reduce latency by factor of concurrent_count

---

## REMOVED Requirements

None (backward compatible, old interfaces preserved).
