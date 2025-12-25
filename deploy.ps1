# Serverless Multi-Tenant SaaS Backend Deployment Script (PowerShell)
# Pakistani Tech Team - Karachi Office

Write-Host "🚀 Deploying Serverless Multi-Tenant SaaS Backend..." -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

# Check prerequisites
Write-Host "📋 Checking prerequisites..." -ForegroundColor Yellow

# Check if AWS CLI is installed
try {
    aws --version | Out-Null
    Write-Host "✅ AWS CLI found" -ForegroundColor Green
} catch {
    Write-Host "❌ AWS CLI not found. Please install and configure AWS CLI first." -ForegroundColor Red
    exit 1
}

# Check if CDK is installed
try {
    cdk --version | Out-Null
    Write-Host "✅ AWS CDK found" -ForegroundColor Green
} catch {
    Write-Host "❌ AWS CDK not found. Installing..." -ForegroundColor Yellow
    npm install -g aws-cdk
}

# Check if Python is installed
try {
    python --version | Out-Null
    Write-Host "✅ Python found" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python 3.9 or later." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Prerequisites check passed!" -ForegroundColor Green

# Install Python dependencies
Write-Host "📦 Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Bootstrap CDK (only needed once per account/region)
Write-Host "🔧 Bootstrapping CDK..." -ForegroundColor Yellow
cdk bootstrap

# Synthesize CloudFormation template
Write-Host "🏗️  Synthesizing CloudFormation template..." -ForegroundColor Yellow
cdk synth

# Deploy the stack
Write-Host "🚀 Deploying to AWS..." -ForegroundColor Yellow
cdk deploy --require-approval never

# Get outputs
Write-Host "📊 Deployment completed! Getting stack outputs..." -ForegroundColor Yellow
aws cloudformation describe-stacks --stack-name SaaSBackendStack --query 'Stacks[0].Outputs' --output table

Write-Host ""
Write-Host "🎉 Deployment successful!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Cyan
Write-Host "1. Note down the API Gateway URL from outputs above"
Write-Host "2. Configure Cognito User Pool (create users/groups)"
Write-Host "3. Test API endpoints with Postman or curl"
Write-Host "4. Set up monitoring dashboards in CloudWatch"
Write-Host ""
Write-Host "🔗 Useful commands:" -ForegroundColor Cyan
Write-Host "  - View logs: aws logs tail /aws/lambda/SaaSBackendStack-CreateTask --follow"
Write-Host "  - Test API: curl -X GET <API_URL>/tasks -H 'Authorization: Bearer <token>'"
Write-Host "  - Destroy stack: cdk destroy"
Write-Host ""
Write-Host "Built with ❤️ by Pakistani tech team for enterprise SaaS solutions" -ForegroundColor Magenta