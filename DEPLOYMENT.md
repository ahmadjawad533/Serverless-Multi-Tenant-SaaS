# Deployment Guide - Serverless Multi-Tenant SaaS Backend

## Quick Start (5 Minutes)

### Prerequisites
```bash
# Install Node.js (for CDK)
# Install Python 3.9+
# Install AWS CLI and configure credentials

# Verify setup
aws sts get-caller-identity
python --version
node --version
```

### Deploy to AWS
```bash
# Clone and navigate to project
cd saas-backend

# Install CDK globally
npm install -g aws-cdk

# Install Python dependencies
pip install -r requirements.txt

# Bootstrap CDK (one-time per account/region)
cdk bootstrap

# Deploy the stack
cdk deploy

# Or use the deployment script
./deploy.sh  # Linux/Mac
./deploy.ps1 # Windows PowerShell
```

## Post-Deployment Setup

### 1. Configure Cognito User Pool
```bash
# Get User Pool ID from CDK outputs
USER_POOL_ID="us-east-1_xxxxxxxxx"

# Create admin user
aws cognito-idp admin-create-user \
    --user-pool-id $USER_POOL_ID \
    --username "ahmed.hassan@karachi-tech.com" \
    --user-attributes Name=email,Value="ahmed.hassan@karachi-tech.com" \
    --temporary-password "TempPass123!" \
    --message-action SUPPRESS

# Create user groups
aws cognito-idp create-group \
    --group-name "Administrators" \
    --user-pool-id $USER_POOL_ID \
    --description "Admin users with full access"

aws cognito-idp create-group \
    --group-name "Members" \
    --user-pool-id $USER_POOL_ID \
    --description "Regular users with limited access"

# Add user to admin group
aws cognito-idp admin-add-user-to-group \
    --user-pool-id $USER_POOL_ID \
    --username "ahmed.hassan@karachi-tech.com" \
    --group-name "Administrators"
```

### 2. Test API Endpoints
```bash
# Get API Gateway URL from CDK outputs
API_URL="https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod"

# Login to get JWT token (use Cognito client)
# Then test endpoints:

# Create task
curl -X POST $API_URL/tasks \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Setup Karachi office network",
    "description": "Configure routers and switches",
    "priority": "HIGH"
  }'

# List tasks
curl -X GET $API_URL/tasks \
  -H "Authorization: Bearer $JWT_TOKEN"

# Update task
curl -X PUT $API_URL/tasks/TASK_ID \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "DONE"}'
```

## Environment Configuration

### Development Environment
```bash
# Set environment variables
export AWS_REGION=us-east-1
export ENVIRONMENT=development
export LOG_LEVEL=DEBUG

# Deploy with development settings
cdk deploy --context environment=development
```

### Production Environment
```bash
# Set production variables
export AWS_REGION=us-east-1
export ENVIRONMENT=production
export LOG_LEVEL=INFO

# Deploy with production settings
cdk deploy --context environment=production
```

## Monitoring Setup

### CloudWatch Dashboards
```bash
# Create custom dashboard
aws cloudwatch put-dashboard \
    --dashboard-name "SaaS-Backend-Metrics" \
    --dashboard-body file://monitoring/dashboard.json
```

### Alarms
```bash
# API Gateway 4xx errors
aws cloudwatch put-metric-alarm \
    --alarm-name "API-4xx-Errors" \
    --alarm-description "High 4xx error rate" \
    --metric-name 4XXError \
    --namespace AWS/ApiGateway \
    --statistic Sum \
    --period 300 \
    --threshold 10 \
    --comparison-operator GreaterThanThreshold

# Lambda errors
aws cloudwatch put-metric-alarm \
    --alarm-name "Lambda-Errors" \
    --alarm-description "Lambda function errors" \
    --metric-name Errors \
    --namespace AWS/Lambda \
    --statistic Sum \
    --period 300 \
    --threshold 5 \
    --comparison-operator GreaterThanThreshold
```

## Security Hardening

### 1. IAM Policies
- Review and tighten IAM permissions
- Enable CloudTrail for audit logging
- Set up AWS Config for compliance

### 2. Network Security
```bash
# Enable VPC Flow Logs (if using VPC)
aws ec2 create-flow-logs \
    --resource-type VPC \
    --resource-ids vpc-xxxxxxxxx \
    --traffic-type ALL \
    --log-destination-type cloud-watch-logs \
    --log-group-name VPCFlowLogs
```

### 3. Data Encryption
- DynamoDB encryption at rest (enabled by default)
- S3 bucket encryption (configured in CDK)
- API Gateway with TLS 1.2+

## Troubleshooting

### Common Issues

#### 1. CDK Bootstrap Failed
```bash
# Check AWS credentials
aws sts get-caller-identity

# Bootstrap with explicit region
cdk bootstrap aws://ACCOUNT-NUMBER/REGION
```

#### 2. Lambda Function Errors
```bash
# View Lambda logs
aws logs tail /aws/lambda/SaaSBackendStack-CreateTask --follow

# Check function configuration
aws lambda get-function --function-name SaaSBackendStack-CreateTask
```

#### 3. DynamoDB Access Issues
```bash
# Check table exists
aws dynamodb describe-table --table-name SaaSAppTable

# Test table access
aws dynamodb scan --table-name SaaSAppTable --limit 1
```

#### 4. API Gateway Issues
```bash
# Check API Gateway logs
aws logs tail /aws/apigateway/SaaSBackendAPI --follow

# Test API Gateway directly
aws apigateway test-invoke-method \
    --rest-api-id API_ID \
    --resource-id RESOURCE_ID \
    --http-method GET
```

## Cost Optimization

### 1. Monitor Costs
```bash
# Set up billing alerts
aws budgets create-budget \
    --account-id ACCOUNT_ID \
    --budget file://billing/budget.json
```

### 2. Optimize Resources
- Use DynamoDB on-demand for variable workloads
- Set Lambda reserved concurrency for cost control
- Enable API Gateway caching for frequently accessed data
- Use S3 lifecycle policies for old audit logs

## Cleanup

### Remove All Resources
```bash
# Destroy the CDK stack
cdk destroy

# Verify all resources are deleted
aws cloudformation list-stacks \
    --stack-status-filter DELETE_COMPLETE
```

## Support

### Logs and Debugging
```bash
# View all Lambda logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/SaaS"

# Export logs for analysis
aws logs create-export-task \
    --log-group-name "/aws/lambda/SaaSBackendStack-CreateTask" \
    --from 1640995200000 \
    --to 1641081600000 \
    --destination "saas-logs-bucket"
```

### Performance Monitoring
```bash
# Enable X-Ray tracing
aws lambda update-function-configuration \
    --function-name SaaSBackendStack-CreateTask \
    --tracing-config Mode=Active
```

---

**Built for Pakistani tech teams who demand enterprise-grade solutions** 🇵🇰