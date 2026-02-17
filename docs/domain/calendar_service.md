# Calendar Service - Domain Context

## Overview

Calendar Service 是 isA 平台的日程管理核心服务，负责用户日历事件的全生命周期管理。作为用户时间规划和任务协调的中心枢纽，它不仅管理本地日历事件，还提供与外部日历系统（Google Calendar、Apple iCloud、Microsoft Outlook）的双向同步能力。

该服务在平台架构中扮演"时间协调层"的角色，与 Task Service、Notification Service、Organization Service 紧密协作，确保用户的时间安排、任务提醒和团队协作无缝衔接。

**Business Context**: 现代用户需要跨平台、跨设备管理日程，Calendar Service 提供统一的日历管理入口和智能提醒机制。

**Core Value Proposition**: 提供一站式日历管理，支持多源日历聚合、智能提醒和团队日程共享。

---

## Business Taxonomy

### Core Entities

#### 1. CalendarEvent（日历事件）
**Definition**: 表示用户日历中的一个时间段内的活动或安排。

**Business Purpose**:
- 记录用户的时间安排和活动计划
- 支持重复性事件的管理
- 提供事件提醒和通知
- 支持事件共享和协作

**Key Attributes**:
- event_id（事件唯一标识符）
- user_id（事件所有者）
- title（事件标题）
- start_time/end_time（开始/结束时间）
- category（事件分类：work/personal/meeting/reminder/holiday/birthday）
- recurrence_type（重复类型：none/daily/weekly/monthly/yearly/custom）
- reminders（提醒时间列表，单位分钟）
- sync_provider（同步来源：local/google/apple/outlook）

**Entity States**:
- **Active**: 事件正常有效
- **Cancelled**: 事件已取消
- **Completed**: 过去的已完成事件

#### 2. SyncStatus（同步状态）
**Definition**: 表示用户与外部日历服务的同步连接状态。

**Business Purpose**:
- 跟踪外部日历同步的健康状态
- 记录最后同步时间和同步数量
- 管理同步错误和重试

**Key Attributes**:
- user_id（用户标识）
- provider（日历提供商）
- status（同步状态：active/error/pending）
- last_sync_time（最后同步时间）
- synced_events_count（同步事件数量）
- error_message（错误信息）

#### 3. RecurrenceRule（重复规则）
**Definition**: 定义事件重复模式的规则配置。

**Business Purpose**:
- 支持复杂的重复模式（如每周二四、每月第一个周一）
- 兼容 iCalendar RRULE 标准
- 计算重复事件的实际发生日期

**Key Attributes**:
- recurrence_type（重复类型）
- recurrence_end_date（重复结束日期）
- recurrence_rule（iCalendar RRULE 格式字符串）

---

## Domain Scenarios

### Scenario 1: Create Calendar Event（创建日历事件）
**Actor**: User
**Trigger**: 用户在应用中创建新的日历事件
**Flow**:
1. 用户提交事件创建请求（标题、时间、分类等）
2. 系统验证开始时间必须早于结束时间
3. 生成唯一的 event_id
4. 存储事件到 PostgreSQL
5. 发布 `calendar.event.created` 事件
6. Notification Service 根据 reminders 设置创建提醒任务
7. 返回创建的事件详情

**Outcome**: 事件成功创建，相关服务收到通知并设置提醒

### Scenario 2: Query Events by Date Range（按日期范围查询事件）
**Actor**: User
**Trigger**: 用户查看某段时间内的日历
**Flow**:
1. 用户指定 user_id、start_date、end_date
2. 可选指定 category 过滤
3. 系统查询符合条件的事件
4. 按时间排序返回事件列表
5. 包含分页信息（total、page、page_size）

**Outcome**: 用户获得指定时间范围内的所有事件

### Scenario 3: Get Today's Events（获取今日事件）
**Actor**: User/System
**Trigger**: 用户打开日历首页或系统晨间推送
**Flow**:
1. 根据 user_id 查询当天 00:00-23:59 的事件
2. 按开始时间排序
3. 返回今日事件列表

**Outcome**: 用户快速了解今天的日程安排

### Scenario 4: Update Calendar Event（更新日历事件）
**Actor**: User
**Trigger**: 用户修改现有事件
**Flow**:
1. 用户提交更新请求（event_id + 更新字段）
2. 验证事件存在且用户有权限
3. 如果修改了时间，验证时间有效性
4. 更新事件记录
5. 发布 `calendar.event.updated` 事件
6. Notification Service 更新提醒任务

**Outcome**: 事件更新成功，相关提醒同步更新

### Scenario 5: Delete Calendar Event（删除日历事件）
**Actor**: User
**Trigger**: 用户删除不需要的事件
**Flow**:
1. 用户提交删除请求（event_id）
2. 验证事件存在且用户有权限
3. 删除事件记录
4. 发布 `calendar.event.deleted` 事件
5. Notification Service 取消相关提醒

**Outcome**: 事件删除成功，相关提醒被取消

### Scenario 6: Sync External Calendar（同步外部日历）
**Actor**: User
**Trigger**: 用户请求同步 Google/Apple/Outlook 日历
**Flow**:
1. 用户提供 provider 和 OAuth credentials
2. 系统调用对应的外部 API
3. 获取外部日历事件
4. 导入/更新到本地数据库
5. 更新 sync_status 记录
6. 返回同步结果（成功数量/错误信息）

**Outcome**: 外部日历事件同步到平台

### Scenario 7: Get Upcoming Events（获取即将到来的事件）
**Actor**: User/System
**Trigger**: 用户查看即将到来的日程或系统推送提醒
**Flow**:
1. 指定 user_id 和 days（默认7天）
2. 查询从现在到 N 天后的事件
3. 按时间排序返回

**Outcome**: 用户获得未来 N 天的日程预览

---

## Domain Events

### Published Events

#### 1. calendar.event.created
**Trigger**: 成功创建新的日历事件后
**Payload**:
- event_id: 事件唯一标识
- user_id: 事件所有者
- title: 事件标题
- start_time: 开始时间（ISO 8601）
- end_time: 结束时间（ISO 8601）
- timestamp: 事件创建时间

**Subscribers**:
- **Notification Service**: 根据 reminders 设置创建提醒任务
- **Audit Service**: 记录事件创建操作
- **Analytics Service**: 统计用户日历使用情况

#### 2. calendar.event.updated
**Trigger**: 成功更新日历事件后
**Payload**:
- event_id: 事件唯一标识
- user_id: 事件所有者
- updated_fields: 修改的字段列表
- timestamp: 更新时间

**Subscribers**:
- **Notification Service**: 更新/重新创建提醒任务
- **Audit Service**: 记录变更历史

#### 3. calendar.event.deleted
**Trigger**: 成功删除日历事件后
**Payload**:
- event_id: 事件唯一标识
- user_id: 事件所有者
- timestamp: 删除时间

**Subscribers**:
- **Notification Service**: 取消所有相关提醒
- **Audit Service**: 记录删除操作
- **Task Service**: 如果事件关联任务，更新任务状态

### Subscribed Events

#### 1. account.user.deleted
**Source**: Account Service
**Handler**: handle_user_deleted
**Side Effects**:
- 删除该用户的所有日历事件
- 删除该用户的同步状态记录

#### 2. organization.member.removed
**Source**: Organization Service
**Handler**: handle_member_removed
**Side Effects**:
- 移除用户对组织共享事件的访问权限
- 清理 organization_id 关联的事件

---

## Core Concepts

### 1. Event Lifecycle（事件生命周期）
1. **Created**: 事件创建，设置提醒
2. **Scheduled**: 事件在计划中，提醒已设置
3. **Reminded**: 已发送提醒通知
4. **In Progress**: 事件进行中（可选）
5. **Completed**: 事件时间已过

### 2. Recurrence Handling（重复事件处理）
- **None**: 一次性事件
- **Daily**: 每天重复
- **Weekly**: 每周重复
- **Monthly**: 每月重复
- **Yearly**: 每年重复
- **Custom**: 自定义 RRULE 规则

### 3. Sync Provider Integration（同步提供商集成）
**Calendar Service owns**:
- 本地事件存储和管理
- 同步状态跟踪
- 事件冲突检测

**Calendar Service does NOT own**:
- OAuth token 管理（Auth Service）
- 用户身份验证（Auth Service）
- 通知发送（Notification Service）
- 任务管理（Task Service）

### 4. Event Sharing Model（事件共享模型）
- is_shared: 是否共享事件
- shared_with: 共享用户列表
- organization_id: 组织级共享

### 5. Timezone Handling（时区处理）
- 所有时间存储为 UTC
- 显示时根据用户时区转换
- 默认时区: UTC

---

## Business Rules (High-Level)

### Event Validation Rules
- **BR-CAL-001**: 事件结束时间必须晚于开始时间
- **BR-CAL-002**: 事件标题为必填字段
- **BR-CAL-003**: 用户只能操作自己的事件（除非是共享事件）
- **BR-CAL-004**: 全天事件忽略具体时分秒
- **BR-CAL-005**: 事件颜色必须是有效的 HEX 格式 (#RRGGBB)

### Recurrence Rules
- **BR-CAL-010**: 重复事件必须指定 recurrence_type
- **BR-CAL-011**: 自定义重复必须提供有效的 RRULE
- **BR-CAL-012**: 重复结束日期必须晚于事件开始日期
- **BR-CAL-013**: 重复事件最多生成 365 个实例

### Reminder Rules
- **BR-CAL-020**: 提醒时间以分钟为单位（如 15, 30, 60）
- **BR-CAL-021**: 单个事件最多设置 5 个提醒
- **BR-CAL-022**: 提醒时间必须为正整数
- **BR-CAL-023**: 提醒在事件开始前触发

### Sync Rules
- **BR-CAL-030**: 每个用户每个提供商只能有一个同步状态
- **BR-CAL-031**: 同步失败不影响本地事件操作
- **BR-CAL-032**: 外部事件通过 external_event_id 去重
- **BR-CAL-033**: 同步冲突时以最后修改时间为准

### Sharing Rules
- **BR-CAL-040**: 共享事件对被共享者只读
- **BR-CAL-041**: 事件所有者可以取消共享
- **BR-CAL-042**: 删除用户时清理其共享关系

### Event Publishing Rules
- **BR-EVT-001**: 所有事件变更（创建/更新/删除）发布对应事件
- **BR-EVT-002**: 事件发布失败只记录日志，不阻塞操作
- **BR-EVT-003**: 事件包含完整上下文供订阅者使用
- **BR-EVT-004**: 所有时间戳使用 ISO 8601 格式

### Data Consistency Rules
- **BR-CON-001**: 事件创建是原子操作（PostgreSQL 事务）
- **BR-CON-002**: 事件更新是原子操作
- **BR-CON-003**: 并发更新使用乐观锁（updated_at 检查）
- **BR-CON-004**: 删除保留审计日志

---

## Calendar Service in the Ecosystem

### Upstream Dependencies
- **Account Service**: 验证用户存在性
- **Auth Service**: OAuth token 管理（外部日历同步）
- **Organization Service**: 组织成员关系验证
- **PostgreSQL gRPC Service**: 持久化存储
- **NATS Event Bus**: 事件发布基础设施
- **Consul**: 服务发现和健康检查
- **API Gateway**: 请求路由和授权

### Downstream Consumers
- **Notification Service**: 创建和管理事件提醒
- **Task Service**: 关联任务与日历事件
- **Device Service**: 设备端日历同步
- **Audit Service**: 操作审计和变更追踪
- **Analytics Service**: 用户行为分析

### Integration Patterns
- **Synchronous REST**: CRUD 操作通过 FastAPI 端点
- **Asynchronous Events**: NATS 用于实时更新
- **Service Discovery**: Consul 用于动态服务定位
- **Protocol Buffers**: PostgreSQL gRPC 通信
- **Health Checks**: `/health` 端点

### Dependency Injection
- **Repository Pattern**: CalendarEventRepository 用于数据访问
- **Protocol Interfaces**: CalendarEventRepositoryProtocol
- **Factory Pattern**: create_calendar_service() 用于生产实例
- **Mock-Friendly**: 协议接口支持测试替身

---

## Success Metrics

### Event Quality Metrics
- **Event Completeness**: 有详细描述的事件比例 (target: >60%)
- **Reminder Usage**: 设置提醒的事件比例 (target: >40%)
- **Sync Adoption**: 使用外部同步的用户比例 (target: >20%)

### Performance Metrics
- **Create Event Latency**: 创建事件响应时间 (target: <100ms)
- **Query Events Latency**: 查询事件列表响应时间 (target: <200ms)
- **Sync Latency**: 外部日历同步时间 (target: <5s)
- **Today Events Latency**: 获取今日事件响应时间 (target: <50ms)

### Availability Metrics
- **Service Uptime**: 服务可用性 (target: 99.9%)
- **Database Connectivity**: PostgreSQL 连接成功率 (target: 99.99%)
- **Event Publishing Success**: 事件发布成功率 (target: >99.5%)
- **External Sync Success**: 外部同步成功率 (target: >95%)

### Business Metrics
- **Events per User**: 每用户平均事件数量
- **Active Calendar Users**: 活跃日历用户数
- **Sync Provider Distribution**: 各同步提供商使用分布
- **Recurring Event Ratio**: 重复事件占比

### System Health Metrics
- **PostgreSQL Query Performance**: 平均查询执行时间
- **NATS Event Throughput**: 每秒发布事件数
- **Consul Registration Health**: 服务注册成功率
- **API Gateway Response Times**: 端到端请求延迟

---

## Glossary

**CalendarEvent**: 日历事件，用户日程中的一个时间段活动
**RecurrenceType**: 重复类型，定义事件如何重复
**EventCategory**: 事件分类，如工作、个人、会议等
**SyncProvider**: 同步提供商，外部日历服务（Google/Apple/Outlook）
**RRULE**: iCalendar 重复规则格式标准
**Reminder**: 提醒，在事件开始前的通知
**All-day Event**: 全天事件，跨越整天的事件
**Timezone**: 时区，用于时间显示转换
**Event Bus**: NATS 消息系统用于异步事件发布
**Repository Pattern**: 数据访问抽象层
**Protocol Interface**: 依赖注入的抽象契约

---

**Document Version**: 1.0
**Last Updated**: 2025-12-17
**Maintained By**: Calendar Service Team
