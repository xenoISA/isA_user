# Task Service - Domain Context

## Overview

The Task Service is the **automation and scheduling engine** for the isA_user platform. It provides centralized task management, execution tracking, scheduled automation, and task analytics. Users can create various types of tasks including daily automations, reminders, todos, calendar events, and custom workflows.

**Business Context**: Enable intelligent task automation that helps users manage their digital lives efficiently. Task Service orchestrates scheduled actions, tracks execution results, and provides insights into task performance and resource consumption.

**Core Value Proposition**: Transform manual repetitive actions into automated workflows with intelligent scheduling, execution tracking, credit management, and comprehensive analytics across task types.

---

## Business Taxonomy

### Core Entities

#### 1. Task
**Definition**: A schedulable work unit that can be executed manually or automatically based on configured triggers.

**Business Purpose**:
- Define what action should be performed
- Specify when and how often to execute
- Track execution history and statistics
- Manage credits consumed per execution
- Support multiple task types for different use cases

**Key Attributes**:
- Task ID (unique identifier)
- User ID (owner of the task)
- Name (display name for the task)
- Description (optional detailed description)
- Task Type (daily_weather, reminder, todo, custom, etc.)
- Status (pending, scheduled, running, completed, failed, cancelled, paused)
- Priority (low, medium, high, urgent)
- Config (JSONB - task-specific configuration)
- Schedule (JSONB - cron/interval settings)
- Credits per Run (resource cost per execution)
- Tags (list of categorization tags)
- Metadata (JSONB - flexible custom data)
- Due Date (optional deadline for todo-type tasks)
- Reminder Time (optional notification trigger)
- Next Run Time (calculated next execution time)

**Task States**:
- **PENDING**: Task created but not yet scheduled
- **SCHEDULED**: Task queued for execution
- **RUNNING**: Task currently executing
- **COMPLETED**: Task successfully completed
- **FAILED**: Task execution failed
- **CANCELLED**: Task cancelled by user or system
- **PAUSED**: Task temporarily suspended

#### 2. Task Execution
**Definition**: A record of a single task execution instance with results and metrics.

**Business Purpose**:
- Track individual execution outcomes
- Record resource consumption (credits, tokens, API calls)
- Store execution results and error details
- Enable execution history analysis
- Support debugging and troubleshooting

**Key Attributes**:
- Execution ID (unique identifier)
- Task ID (reference to parent task)
- User ID (task owner)
- Status (running, completed, failed, cancelled)
- Trigger Type (manual, scheduled, webhook)
- Trigger Data (JSONB - execution context)
- Result (JSONB - execution output)
- Error Message (if failed)
- Error Details (JSONB - detailed error info)
- Credits Consumed (actual credits used)
- Tokens Used (LLM tokens if applicable)
- API Calls Made (external API call count)
- Duration MS (execution time in milliseconds)
- Started At (execution start timestamp)
- Completed At (execution end timestamp)

#### 3. Task Template
**Definition**: A predefined task configuration that users can instantiate for common automation patterns.

**Business Purpose**:
- Accelerate task creation with pre-configured settings
- Standardize common automation patterns
- Control access based on subscription level
- Provide guided task setup experience

**Key Attributes**:
- Template ID (unique identifier)
- Name (template display name)
- Description (what this template does)
- Category (grouping for UI display)
- Task Type (target task type)
- Default Config (JSONB - preconfigured settings)
- Required Fields (fields user must provide)
- Optional Fields (fields user may customize)
- Config Schema (JSONB - validation rules)
- Required Subscription Level (free, basic, pro, enterprise)
- Credits per Run (estimated cost)
- Tags (categorization tags)
- Is Active (availability status)

#### 4. Task Analytics
**Definition**: Aggregated statistics and insights about a user's task portfolio.

**Business Purpose**:
- Provide visibility into task performance
- Track resource consumption trends
- Identify optimization opportunities
- Support billing and quota management

**Key Attributes**:
- User ID (owner)
- Time Period (analysis window)
- Total Tasks (count of all tasks)
- Active Tasks (currently scheduled)
- Completed Tasks (finished successfully)
- Failed Tasks (execution failures)
- Paused Tasks (temporarily suspended)
- Total Executions (execution count)
- Successful Executions (success count)
- Failed Executions (failure count)
- Success Rate (percentage)
- Average Execution Time (in seconds)
- Total Credits Consumed (resource usage)
- Total Tokens Used (LLM usage)
- Total API Calls (external calls)
- Task Types Distribution (breakdown by type)
- Busiest Hours (peak execution hours)
- Busiest Days (peak execution days)

---

## Domain Scenarios

### Scenario 1: Create Daily Weather Task
**Actor**: User, Mobile App
**Trigger**: User wants daily weather updates
**Flow**:
1. User selects "Daily Weather" template in app
2. App calls `POST /api/v1/tasks` with task_type=daily_weather
3. Task Service validates user subscription level
4. Task Service validates task configuration (location, time)
5. Creates task record with schedule configuration
6. Calculates next_run_time based on schedule
7. Publishes `task.created` event to NATS
8. Returns task details to user
9. Scheduler picks up task at scheduled time
10. Executes weather API call and sends notification

**Outcome**: User receives daily weather notification at configured time

### Scenario 2: Manual Task Execution
**Actor**: User, Web App
**Trigger**: User clicks "Run Now" on a task
**Flow**:
1. User clicks run button for task_id=task_123
2. App calls `POST /api/v1/tasks/{task_id}/execute`
3. Task Service validates task ownership
4. Creates execution record with status=running
5. Executes task logic (API calls, processing)
6. Updates task execution statistics
7. Updates execution record with result/error
8. Publishes `task.executed` event
9. Returns execution result to user
10. Deducts credits from user's wallet

**Outcome**: Task executed immediately with tracked results

### Scenario 3: Create Todo Task with Reminder
**Actor**: User, Mobile App
**Trigger**: User creates a new todo item
**Flow**:
1. User enters "Buy groceries" with due date and reminder
2. App calls `POST /api/v1/tasks` with task_type=todo
3. Task Service validates todo data
4. Creates task with due_date and reminder_time
5. Schedules reminder notification
6. Returns task to user
7. At reminder_time, notification triggered
8. User marks task complete
9. App calls `PUT /api/v1/tasks/{task_id}` with status=completed
10. Task marked complete, no further reminders

**Outcome**: Todo tracked with timely reminder

### Scenario 4: Task Failure and Retry
**Actor**: System, Scheduler
**Trigger**: Scheduled task fails during execution
**Flow**:
1. Scheduler triggers task_id=task_456
2. Task Service creates execution record
3. Task execution fails (external API error)
4. Execution record updated with error details
5. Task failure_count incremented
6. Publishes `task.failed` event
7. User notified of failure (optional)
8. Task remains scheduled for next run
9. User can view execution history for debugging
10. User can manually retry via "Run Now"

**Outcome**: Failure tracked, user informed, automatic retry on schedule

### Scenario 5: Task Analytics Review
**Actor**: User, Dashboard
**Trigger**: User views task analytics
**Flow**:
1. User opens analytics dashboard
2. Dashboard calls `GET /api/v1/tasks/analytics?days=30`
3. Task Service aggregates 30-day statistics
4. Queries task counts by status
5. Aggregates execution metrics
6. Calculates success rates and timing patterns
7. Returns TaskAnalyticsResponse
8. Dashboard displays charts and metrics
9. User identifies underperforming tasks
10. User optimizes task configurations

**Outcome**: User gains insights into task performance and resource usage

### Scenario 6: Browse and Use Templates
**Actor**: User, Mobile App
**Trigger**: User wants to create a new automated task
**Flow**:
1. User opens "Add Task" flow
2. App calls `GET /api/v1/templates?subscription_level=pro`
3. Task Service filters templates by subscription
4. Returns available templates for user's tier
5. User selects "Daily News Digest" template
6. App shows template configuration form
7. User customizes required fields
8. App calls `POST /api/v1/tasks` with template config
9. Task created from template
10. Task scheduled for execution

**Outcome**: Quick task creation from pre-configured template

### Scenario 7: User Deleted - Cancel Tasks
**Actor**: System, Account Service
**Trigger**: User account deleted
**Flow**:
1. Account Service publishes `user.deleted` event
2. Task Service receives event
3. Event handler calls `cancel_user_tasks(user_id)`
4. All pending/scheduled tasks cancelled
5. Running tasks allowed to complete
6. Task Service logs cleanup action
7. No further executions for this user
8. Analytics data retained for audit

**Outcome**: User's tasks cleaned up, no orphaned executions

---

## Domain Events

### Published Events

#### 1. task.created
**Trigger**: New task successfully created via `POST /api/v1/tasks`
**Payload**:
- task_id: Unique task identifier
- user_id: Task owner
- task_type: Type of task
- name: Task name
- schedule: Schedule configuration
- created_at: Creation timestamp

**Subscribers**:
- **Audit Service**: Log task creation
- **Analytics Service**: Track task creation metrics
- **Notification Service**: Send task creation confirmation

#### 2. task.updated
**Trigger**: Task configuration modified via `PUT /api/v1/tasks/{task_id}`
**Payload**:
- task_id: Task identifier
- user_id: Task owner
- updated_fields: List of changed fields
- updated_at: Update timestamp

**Subscribers**:
- **Audit Service**: Track configuration changes
- **Calendar Service**: Update linked calendar events

#### 3. task.executed
**Trigger**: Task execution completed (success or failure)
**Payload**:
- task_id: Task identifier
- execution_id: Execution record ID
- user_id: Task owner
- status: Execution status (completed/failed)
- credits_consumed: Credits used
- duration_ms: Execution duration
- executed_at: Execution timestamp

**Subscribers**:
- **Billing Service**: Process credit consumption
- **Wallet Service**: Deduct credits
- **Analytics Service**: Track execution metrics
- **Notification Service**: Send execution result notification

#### 4. task.deleted
**Trigger**: Task soft-deleted via `DELETE /api/v1/tasks/{task_id}`
**Payload**:
- task_id: Task identifier
- user_id: Task owner
- deleted_at: Deletion timestamp

**Subscribers**:
- **Audit Service**: Log task deletion
- **Calendar Service**: Remove linked calendar events

#### 5. task.status_changed
**Trigger**: Task status changed (scheduled, paused, cancelled)
**Payload**:
- task_id: Task identifier
- user_id: Task owner
- old_status: Previous status
- new_status: New status
- reason: Status change reason
- changed_at: Timestamp

**Subscribers**:
- **Notification Service**: Notify user of status change
- **Analytics Service**: Update task status metrics

#### 6. task.reminder_triggered
**Trigger**: Task reminder time reached
**Payload**:
- task_id: Task identifier
- user_id: Task owner
- reminder_type: Type of reminder
- triggered_at: Timestamp

**Subscribers**:
- **Notification Service**: Send reminder notification
- **MQTT Channel**: Push to user devices

### Subscribed Events

#### 1. account_service.user.deleted
**Source**: account_service
**Purpose**: Cancel all tasks when user is deleted

**Payload**:
- user_id: User ID
- timestamp: Deletion timestamp
- reason: Deletion reason

**Handler Action**: Cancel all pending/scheduled tasks for user

#### 2. subscription_service.subscription.changed
**Source**: subscription_service
**Purpose**: Update task limits based on subscription tier

**Payload**:
- user_id: User ID
- old_tier: Previous subscription tier
- new_tier: New subscription tier

**Handler Action**: Adjust task limits and template access

#### 3. calendar_service.event.created
**Source**: calendar_service
**Purpose**: Create linked task for calendar event (if configured)

**Payload**:
- event_id: Calendar event ID
- user_id: User ID
- title: Event title
- start_time: Event start time

**Handler Action**: Create reminder task for calendar event

---

## Core Concepts

### Task Lifecycle
1. **Creation**: User creates task via API → validated → stored → scheduled
2. **Scheduling**: Task added to execution queue based on schedule
3. **Execution**: Scheduler triggers task → execution record created → logic runs
4. **Completion**: Result stored → statistics updated → event published
5. **Failure Handling**: Error recorded → user notified → retries on schedule
6. **Cancellation**: User or system cancels → no further executions
7. **Deletion**: Soft delete → task no longer visible but data preserved

### Task Types
**Built-in Types**:
- **DAILY_WEATHER**: Fetch and report weather for location
- **DAILY_NEWS**: Aggregate news from configured sources
- **NEWS_MONITOR**: Monitor topics and alert on matches
- **WEATHER_ALERT**: Alert on weather condition changes
- **PRICE_TRACKER**: Track product prices and alert on changes
- **DATA_BACKUP**: Scheduled data backup operations
- **TODO**: Simple todo item with optional reminder
- **REMINDER**: Standalone reminder without task logic
- **CALENDAR_EVENT**: Task linked to calendar
- **CUSTOM**: User-defined custom task logic

### Priority Levels
- **LOW**: Background tasks, no urgency
- **MEDIUM**: Standard priority (default)
- **HIGH**: Important tasks, prioritized execution
- **URGENT**: Critical tasks, immediate attention

### Execution Model
- **Manual**: User triggers execution on demand
- **Scheduled**: Cron-based or interval scheduling
- **Webhook**: External trigger via webhook endpoint
- **Event**: Triggered by NATS events

### Credit System
- Tasks consume credits based on complexity
- Credits deducted after successful execution
- Failed executions may consume partial credits
- Users have credit limits based on subscription
- Analytics track total credit consumption

---

## Business Rules (High-Level)

### Task Creation Rules
- **BR-TSK-001**: Task ID must be unique (generated UUID)
- **BR-TSK-002**: User ID must reference valid account
- **BR-TSK-003**: Task name must be 1-255 characters
- **BR-TSK-004**: Task type must be from valid TaskType enum
- **BR-TSK-005**: Default status is PENDING on creation
- **BR-TSK-006**: Default priority is MEDIUM
- **BR-TSK-007**: Credits per run must be >= 0
- **BR-TSK-008**: Schedule must be valid cron/interval if provided
- **BR-TSK-009**: Tags must be list of non-empty strings

### Task Update Rules
- **BR-UPD-001**: Only task owner can update task
- **BR-UPD-002**: Task ID cannot be changed
- **BR-UPD-003**: Task type cannot be changed after creation
- **BR-UPD-004**: Status changes must follow valid transitions
- **BR-UPD-005**: Updated_at automatically set on every update
- **BR-UPD-006**: Deleted tasks cannot be updated

### Task Execution Rules
- **BR-EXE-001**: Only active tasks can be executed
- **BR-EXE-002**: Deleted/cancelled tasks cannot be executed
- **BR-EXE-003**: Execution record created before execution starts
- **BR-EXE-004**: Credits consumed only on successful completion
- **BR-EXE-005**: Failed executions increment failure_count
- **BR-EXE-006**: Successful executions increment success_count
- **BR-EXE-007**: Execution duration tracked in milliseconds
- **BR-EXE-008**: Maximum execution time enforced (timeout)

### Schedule Rules
- **BR-SCH-001**: Scheduled tasks must have valid schedule config
- **BR-SCH-002**: Next run time calculated from schedule
- **BR-SCH-003**: Missed runs handled based on catch-up policy
- **BR-SCH-004**: Paused tasks skip scheduled executions
- **BR-SCH-005**: Cancelled tasks removed from schedule

### Status Transition Rules
- **BR-STS-001**: PENDING → SCHEDULED (on schedule set)
- **BR-STS-002**: SCHEDULED → RUNNING (on execution start)
- **BR-STS-003**: RUNNING → COMPLETED (on success)
- **BR-STS-004**: RUNNING → FAILED (on failure)
- **BR-STS-005**: SCHEDULED → PAUSED (on pause)
- **BR-STS-006**: PAUSED → SCHEDULED (on resume)
- **BR-STS-007**: Any → CANCELLED (on cancel)
- **BR-STS-008**: CANCELLED is terminal (cannot transition out)

### Template Rules
- **BR-TPL-001**: Template ID must be unique
- **BR-TPL-002**: Required subscription level enforced
- **BR-TPL-003**: Only active templates returned in queries
- **BR-TPL-004**: Default config merged with user config
- **BR-TPL-005**: Required fields must be provided by user

### Analytics Rules
- **BR-ANA-001**: Analytics aggregated per user
- **BR-ANA-002**: Time period defaults to 30 days
- **BR-ANA-003**: Success rate calculated as successes/total
- **BR-ANA-004**: Deleted tasks excluded from active counts
- **BR-ANA-005**: Analytics cached with short TTL (5 minutes)

---

## Task Service in the Ecosystem

### Upstream Dependencies
- **Account Service**: User identity and subscription level
- **Auth Service**: Request authentication
- **PostgreSQL gRPC Service**: Persistent storage
- **NATS Event Bus**: Event publishing and subscription
- **Consul**: Service discovery and health checks
- **API Gateway**: Request routing and authorization

### Downstream Consumers
- **Notification Service**: Send task reminders and results
- **Calendar Service**: Sync task schedules with calendar
- **Billing Service**: Process credit consumption
- **Wallet Service**: Deduct credits from user wallet
- **Audit Service**: Track task changes for compliance
- **Analytics Service**: Aggregate task metrics

### Integration Patterns
- **Synchronous REST**: CRUD operations via FastAPI endpoints
- **Asynchronous Events**: NATS for real-time updates
- **Service Discovery**: Consul for dynamic service location
- **Protocol Buffers**: PostgreSQL gRPC communication
- **MQTT**: Real-time notifications to user devices

### Dependency Injection
- **Repository Pattern**: TaskRepository for data access
- **Protocol Interfaces**: TaskRepositoryProtocol, EventBusProtocol
- **Factory Pattern**: create_task_service() for production instances
- **Client Protocols**: NotificationClientProtocol, CalendarClientProtocol

---

## Success Metrics

### Task Quality Metrics
- **Task Creation Success Rate**: % of task creations that succeed (target: >99%)
- **Execution Success Rate**: % of executions that complete successfully (target: >95%)
- **Schedule Accuracy**: % of scheduled tasks that run on time (target: >99%)
- **Template Usage Rate**: % of tasks created from templates

### Performance Metrics
- **Task Creation Latency**: Time to create task (target: <200ms)
- **Execution Start Latency**: Time from scheduled to running (target: <5s)
- **Average Execution Duration**: Mean execution time per task type
- **API Response Time**: 95th percentile API latency (target: <100ms)

### Resource Metrics
- **Credits Consumed**: Total credits consumed per user per period
- **Tokens Used**: LLM tokens consumed per task type
- **API Calls Made**: External API calls per execution
- **Storage Used**: Data storage per user's tasks

### Business Metrics
- **Daily Active Tasks**: Tasks executed per day
- **User Task Count**: Average tasks per user
- **Task Diversity**: Distribution across task types
- **Retention Rate**: Users with tasks after 30 days

---

## Glossary

**Task**: Schedulable work unit with configuration and execution tracking
**Execution**: Single instance of task running with results
**Template**: Pre-configured task definition for quick setup
**Schedule**: Cron or interval configuration for automatic execution
**Credits**: Resource currency consumed by task execution
**Priority**: Urgency level affecting execution order
**Status**: Current state in task lifecycle
**Trigger**: What initiates task execution (manual, scheduled, webhook)
**Config**: Task-specific settings stored as JSONB
**Metadata**: Flexible additional data attached to task
**Analytics**: Aggregated statistics about task performance
**Due Date**: Deadline for todo-type tasks
**Reminder**: Notification triggered at specified time
**Soft Delete**: Marking task deleted while preserving data

---

**Document Version**: 1.0
**Last Updated**: 2025-12-17
**Maintained By**: Task Service Team
