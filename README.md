# Serverless Multi-Tenant SaaS Backend

**Team Task Management API - Enterprise-Grade Serverless Architecture**

## Problem Statement

Traditional multi-tenant SaaS applications face several critical challenges:
- **Database isolation complexity**: Separate databases per tenant don't scale
- **Infrastructure overhead**: Managing multiple environments is expensive
- **Performance bottlenecks**: Synchronous processing limits user experience
- **Security concerns**: Tenant data leakage risks in shared systems

This project demonstrates a **logical tenant isolation** approach using AWS serverless services, achieving enterprise-grade security and scalability without the operational overhead of physical separation.

## Architecture Overview

```
Client Application
        ↓
    API Gateway (HTTP API)
        ↓
    Lambda Functions (Auth → Business Logic)
        ↓
    DynamoDB (Single Table Design)
        ↓
    EventBridge (Asynchronous Processing)
        ↓
    Background Lambda Functions

Static Assets/Exports → S3
Authentication → Cognito User Pool
Monitoring → CloudWatch
```

### Why Serverless?

1. **Zero Infrastructure Management**: No servers to patch or scale
2. **Pay-per-Use**: Only pay for actual requests and compute time
3. **Automatic Scaling**: Handles traffic spikes without configuration
4. **Built-in Security**: AWS handles security patches and compliance
5. **Developer Velocity**: Focus on business logic, not infrastructure

## Request Flow Example

### Task Creation Flow
```
1. Client → POST /tasks (with JWT token)
2. API Gateway → Validates request format
3. Lambda Authorizer → Validates JWT + extracts tenant_id
4. Task Lambda → Validates permissions + writes to DynamoDB
5. EventBridge → Publishes TaskCreated event
6. Background Lambdas → Process analytics, notifications, audit logs
7. Response → Returns task details to client
```

## Security Model

### Multi-Tenant Isolation Strategy

**Logical Isolation (Our Approach)**:
- Single DynamoDB table with tenant_id in partition key
- Row-level security through application logic
- Shared infrastructure with isolated data access
- Cost-effective and scalable

**Why Not Physical Isolation?**:
- Separate databases per tenant = 1000 tenants = 1000 databases
- Management nightmare at scale
- Exponentially increasing costs
- Complex backup and disaster recovery

### Authentication & Authorization

1. **Cognito User Pool**: Handles user registration, login, password reset
2. **JWT Tokens**: Stateless authentication with tenant_id claims
3. **Lambda Authorizer**: Validates tokens and extracts tenant context
4. **Role-Based Access Control**:
   - `ADMIN`: Full CRUD operations on tasks
   - `MEMBER`: Read tasks, create tasks, update own tasks

### Data Security

- All DynamoDB queries include tenant_id filter
- IAM policies restrict Lambda access to specific table operations
- EventBridge rules ensure events stay within tenant boundaries
- CloudWatch logs exclude sensitive data

## DynamoDB Single Table Design

### Table Structure
```
Table: SaaSAppTable
Partition Key: PK (String)
Sort Key: SK (String)
```

### Access Patterns

| Entity | PK | SK | Attributes |
|--------|----|----|------------|
| Task | `TENANT#karachi-tech` | `TASK#task-123` | title, status, created_at, assigned_to |
| User | `TENANT#karachi-tech` | `USER#ahmed-ali` | email, role, created_at, last_login |
| Organization | `TENANT#karachi-tech` | `ORG#metadata` | name, plan, created_at, settings |

### Query Examples

**Get all tasks for tenant:**
```python
response = table.query(
    KeyConditionExpression=Key('PK').eq('TENANT#karachi-tech') & 
                          Key('SK').begins_with('TASK#')
)
```

**Get specific task:**
```python
response = table.get_item(
    Key={
        'PK': 'TENANT#karachi-tech',
        'SK': 'TASK#task-123'
    }
)
```

### Why Single Table?

1. **Performance**: Single-digit millisecond latency
2. **Cost**: One table vs hundreds of tables
3. **Simplicity**: One backup strategy, one monitoring setup
4. **Scalability**: DynamoDB handles partitioning automatically

## API Endpoints

### Task Management

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/tasks` | Create new task | Yes |
| GET | `/tasks` | List tenant tasks | Yes |
| PUT | `/tasks/{id}` | Update task | Yes |
| DELETE | `/tasks/{id}` | Delete task | Yes (ADMIN only) |

### Request/Response Examples

**Create Task:**
```json
POST /tasks
{
  "title": "Setup CI/CD pipeline for Lahore office",
  "description": "Configure GitHub Actions for automated deployments",
  "assigned_to": "hassan.malik@company.pk"
}

Response:
{
  "task_id": "task-uuid-123",
  "tenant_id": "karachi-tech",
  "title": "Setup CI/CD pipeline for Lahore office",
  "status": "OPEN",
  "created_at": "2024-01-15T10:30:00Z",
  "assigned_to": "hassan.malik@company.pk"
}
```

## Asynchronous Event Processing

### Why Async Matters

1. **User Experience**: API responds immediately, heavy processing happens in background
2. **Reliability**: Failed background tasks can be retried without affecting user
3. **Scalability**: Decouple request processing from business logic
4. **Flexibility**: Easy to add new event handlers without changing core API

### Event Flow

```
Task Created → EventBridge → Multiple Handlers:
├── Analytics Lambda (update metrics)
├── Notification Lambda (send emails/Slack)
├── Audit Lambda (compliance logging)
└── Integration Lambda (sync with external systems)
```

## Cost Estimation (Monthly - Small Scale)

**Assumptions**: 10 tenants, 1000 tasks/month, 5000 API calls/month

| Service | Usage | Cost (USD) |
|---------|-------|------------|
| Lambda | 5000 requests, 1GB memory | $0.20 |
| DynamoDB | 1GB storage, on-demand | $1.25 |
| API Gateway | 5000 HTTP API calls | $0.005 |
| EventBridge | 1000 events | $0.001 |
| Cognito | 1000 MAU | $0.55 |
| S3 | 1GB storage | $0.023 |
| CloudWatch | Basic monitoring | $0.50 |
| **Total** | | **~$2.50/month** |

**Why This Is Cheap**:
- No idle server costs (pay only for actual usage)
- AWS Free Tier covers most Lambda and DynamoDB usage
- Shared infrastructure across all tenants
- No database licensing fees

## Failure Scenarios & Mitigation

### Lambda Function Failures
- **Problem**: Function timeout or error
- **Mitigation**: Dead letter queues, automatic retries, CloudWatch alarms

### DynamoDB Throttling
- **Problem**: Hot partition or burst capacity exceeded
- **Mitigation**: On-demand billing, proper partition key design

### API Gateway Limits
- **Problem**: Rate limiting or quota exceeded
- **Mitigation**: Usage plans, caching, request throttling

### Cognito Service Issues
- **Problem**: Authentication service unavailable
- **Mitigation**: Multiple regions, cached tokens, graceful degradation

## Future Improvements

### Phase 2 Enhancements
- **Multi-region deployment**: Global availability and disaster recovery
- **Advanced analytics**: Real-time dashboards with QuickSight
- **File attachments**: S3 integration with presigned URLs
- **Real-time updates**: WebSocket API for live task updates

### Phase 3 Scaling
- **GraphQL API**: More flexible client queries
- **Elasticsearch**: Advanced search and filtering
- **Machine learning**: Task priority prediction, workload optimization
- **Mobile SDK**: Native iOS/Android libraries

## Development Setup

### Prerequisites
- Python 3.9+
- AWS CLI configured
- AWS CDK installed (`npm install -g aws-cdk`)
- Docker (for local testing)

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Deploy to AWS
cdk deploy
```

### Environment Variables
```bash
DYNAMODB_TABLE_NAME=SaaSAppTable
COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
EVENTBRIDGE_BUS_NAME=saas-events
LOG_LEVEL=INFO
```

---

**Built with ❤️ for Pakistani tech teams who demand enterprise-grade solutions**