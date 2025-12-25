"""
Main CDK Stack for Serverless Multi-Tenant SaaS Backend
Defines all AWS resources needed for the task management API
"""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_dynamodb as dynamodb,
    aws_cognito as cognito,
    aws_events as events,
    aws_events_targets as targets,
    aws_s3 as s3,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct
import os


class SaaSBackendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # DynamoDB Single Table
        self.dynamodb_table = self._create_dynamodb_table()
        
        # Cognito User Pool for Authentication
        self.user_pool = self._create_cognito_user_pool()
        
        # EventBridge Custom Bus
        self.event_bus = self._create_event_bus()
        
        # S3 Bucket for Static Assets
        self.s3_bucket = self._create_s3_bucket()
        
        # Lambda Functions
        self.lambda_functions = self._create_lambda_functions()
        
        # API Gateway
        self.api_gateway = self._create_api_gateway()
        
        # EventBridge Rules and Targets
        self._create_event_rules()

    def _create_dynamodb_table(self) -> dynamodb.Table:
        """Create single DynamoDB table for multi-tenant data"""
        table = dynamodb.Table(
            self, "SaaSAppTable",
            table_name="SaaSAppTable",
            partition_key=dynamodb.Attribute(
                name="PK",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK", 
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.ON_DEMAND,
            removal_policy=RemovalPolicy.DESTROY,  # For demo purposes
            point_in_time_recovery=True,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES
        )
        
        # GSI for querying by tenant and status
        table.add_global_secondary_index(
            index_name="GSI1",
            partition_key=dynamodb.Attribute(
                name="GSI1PK",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="GSI1SK",
                type=dynamodb.AttributeType.STRING
            )
        )
        
        return table

    def _create_cognito_user_pool(self) -> cognito.UserPool:
        """Create Cognito User Pool for authentication"""
        user_pool = cognito.UserPool(
            self, "SaaSUserPool",
            user_pool_name="saas-backend-users",
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # User Pool Client
        user_pool.add_client(
            "SaaSUserPoolClient",
            user_pool_client_name="saas-backend-client",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True
            ),
            generate_secret=False,  # For frontend apps
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30)
        )
        
        return user_pool

    def _create_event_bus(self) -> events.EventBus:
        """Create custom EventBridge bus for SaaS events"""
        return events.EventBus(
            self, "SaaSEventBus",
            event_bus_name="saas-backend-events"
        )

    def _create_s3_bucket(self) -> s3.Bucket:
        """Create S3 bucket for static assets and exports"""
        return s3.Bucket(
            self, "SaaSAssetsBucket",
            bucket_name=f"saas-backend-assets-{self.account}-{self.region}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldVersions",
                    noncurrent_version_expiration=Duration.days(30)
                )
            ]
        )

    def _create_lambda_functions(self) -> dict:
        """Create all Lambda functions for the API"""
        
        # Common Lambda environment variables
        common_env = {
            "DYNAMODB_TABLE_NAME": self.dynamodb_table.table_name,
            "USER_POOL_ID": self.user_pool.user_pool_id,
            "EVENT_BUS_NAME": self.event_bus.event_bus_name,
            "S3_BUCKET_NAME": self.s3_bucket.bucket_name,
            "LOG_LEVEL": "INFO"
        }
        
        # Lambda execution role
        lambda_role = iam.Role(
            self, "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ]
        )
        
        # Grant permissions to Lambda role
        self.dynamodb_table.grant_read_write_data(lambda_role)
        self.event_bus.grant_put_events_to(lambda_role)
        self.s3_bucket.grant_read_write(lambda_role)
        
        functions = {}
        
        # Task Management Functions
        task_functions = [
            ("CreateTask", "services/tasks/create_task.py"),
            ("ListTasks", "services/tasks/list_tasks.py"), 
            ("UpdateTask", "services/tasks/update_task.py"),
            ("DeleteTask", "services/tasks/delete_task.py")
        ]
        
        for func_name, handler_path in task_functions:
            functions[func_name] = _lambda.Function(
                self, func_name,
                runtime=_lambda.Runtime.PYTHON_3_9,
                handler=f"{os.path.basename(handler_path).replace('.py', '')}.handler",
                code=_lambda.Code.from_asset("services"),
                environment=common_env,
                role=lambda_role,
                timeout=Duration.seconds(30),
                memory_size=256,
                log_retention=logs.RetentionDays.ONE_WEEK
            )
        
        # Event Handler Functions
        functions["TaskCreatedHandler"] = _lambda.Function(
            self, "TaskCreatedHandler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="task_created_handler.handler",
            code=_lambda.Code.from_asset("events"),
            environment=common_env,
            role=lambda_role,
            timeout=Duration.seconds(60),
            memory_size=256,
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # Lambda Authorizer
        functions["Authorizer"] = _lambda.Function(
            self, "LambdaAuthorizer",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="authorizer.handler",
            code=_lambda.Code.from_asset("services/auth"),
            environment=common_env,
            role=lambda_role,
            timeout=Duration.seconds(10),
            memory_size=128,
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        return functions

    def _create_api_gateway(self) -> apigateway.RestApi:
        """Create API Gateway with Lambda integrations"""
        
        # Lambda Authorizer
        authorizer = apigateway.TokenAuthorizer(
            self, "JWTAuthorizer",
            handler=self.lambda_functions["Authorizer"],
            token_source=apigateway.IdentitySource.header("Authorization"),
            results_cache_ttl=Duration.minutes(5)
        )
        
        # REST API
        api = apigateway.RestApi(
            self, "SaaSBackendAPI",
            rest_api_name="saas-backend-api",
            description="Multi-Tenant SaaS Backend API",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"]
            ),
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                throttling_rate_limit=1000,
                throttling_burst_limit=2000,
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True
            )
        )
        
        # Tasks resource
        tasks_resource = api.root.add_resource("tasks")
        
        # POST /tasks
        tasks_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.lambda_functions["CreateTask"]),
            authorizer=authorizer
        )
        
        # GET /tasks
        tasks_resource.add_method(
            "GET", 
            apigateway.LambdaIntegration(self.lambda_functions["ListTasks"]),
            authorizer=authorizer
        )
        
        # Individual task resource
        task_resource = tasks_resource.add_resource("{id}")
        
        # PUT /tasks/{id}
        task_resource.add_method(
            "PUT",
            apigateway.LambdaIntegration(self.lambda_functions["UpdateTask"]),
            authorizer=authorizer
        )
        
        # DELETE /tasks/{id}
        task_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(self.lambda_functions["DeleteTask"]),
            authorizer=authorizer
        )
        
        return api

    def _create_event_rules(self):
        """Create EventBridge rules for async processing"""
        
        # Rule for TaskCreated events
        task_created_rule = events.Rule(
            self, "TaskCreatedRule",
            event_bus=self.event_bus,
            event_pattern=events.EventPattern(
                source=["saas.tasks"],
                detail_type=["Task Created"]
            ),
            description="Route task created events to processing Lambda"
        )
        
        # Add Lambda target
        task_created_rule.add_target(
            targets.LambdaFunction(self.lambda_functions["TaskCreatedHandler"])
        )