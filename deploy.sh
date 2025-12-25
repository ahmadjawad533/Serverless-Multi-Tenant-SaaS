#!/bin/bash

# Serverless Multi-Tenant SaaS Backend Deployment Script
# Pakistani Tech Team - Karachi Office

set -e

echo "🚀 Deploying Serverless Multi-Tenant SaaS Backend..."
echo "=================================================="

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check if AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install and configure AWS CLI first."
    exit 1
fi

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    echo "❌ AWS CDK not found. Installing..."
    npm install -g aws-cdk
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.9 or later."
    exit 1
fi

echo "✅ Prerequisites check passed!"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Bootstrap CDK (only needed once per account/region)
echo "🔧 Bootstrapping CDK..."
cdk bootstrap

# Synthesize CloudFormation template
echo "🏗️  Synthesizing CloudFormation template..."
cdk synth

# Deploy the stack
echo "🚀 Deploying to AWS..."
cdk deploy --require-approval never

# Get outputs
echo "📊 Deployment completed! Getting stack outputs..."
aws cloudformation describe-stacks \
    --stack-name SaaSBackendStack \
    --query 'Stacks[0].Outputs' \
    --output table

echo ""
echo "🎉 Deployment successful!"
echo ""
echo "📝 Next steps:"
echo "1. Note down the API Gateway URL from outputs above"
echo "2. Configure Cognito User Pool (create users/groups)"
echo "3. Test API endpoints with Postman or curl"
echo "4. Set up monitoring dashboards in CloudWatch"
echo ""
echo "🔗 Useful commands:"
echo "  - View logs: aws logs tail /aws/lambda/SaaSBackendStack-CreateTask --follow"
echo "  - Test API: curl -X GET <API_URL>/tasks -H 'Authorization: Bearer <token>'"
echo "  - Destroy stack: cdk destroy"
echo ""
echo "Built with ❤️ by Pakistani tech team for enterprise SaaS solutions"