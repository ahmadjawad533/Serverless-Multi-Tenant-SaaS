#!/usr/bin/env python3
"""
AWS CDK App Entry Point
Multi-Tenant SaaS Backend Infrastructure
"""

import aws_cdk as cdk
from stack import SaaSBackendStack

app = cdk.App()

# Main stack for the SaaS backend
SaaSBackendStack(
    app, 
    "SaaSBackendStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1"
    ),
    description="Serverless Multi-Tenant SaaS Backend - Task Management API"
)

app.synth()