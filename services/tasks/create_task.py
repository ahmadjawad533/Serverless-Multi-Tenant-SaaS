"""
Create Task Lambda Function
Handles POST /tasks endpoint for creating new tasks
"""

import json
import uuid
import boto3
from datetime import datetime
from typing import Dict, Any
import os
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))

# AWS clients
dynamodb = boto3.resource('dynamodb')
eventbridge = boto3.client('events')

# Environment variables
TABLE_NAME = os.getenv('DYNAMODB_TABLE_NAME')
EVENT_BUS_NAME = os.getenv('EVENT_BUS_NAME')

table = dynamodb.Table(TABLE_NAME)


def handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda handler for creating tasks
    
    Expected event structure:
    {
        "body": "{\"title\": \"Task title\", \"description\": \"Task description\"}",
        "requestContext": {
            "authorizer": {
                "tenant_id": "karachi-tech",
                "user_id": "ahmed-ali",
                "role": "ADMIN"
            }
        }
    }
    """
    try:
        # Extract tenant context from authorizer
        authorizer = event['requestContext']['authorizer']
        tenant_id = authorizer['tenant_id']
        user_id = authorizer['user_id']
        user_role = authorizer['role']
        
        # Parse request body
        body = json.loads(event['body'])
        
        # Validate required fields
        if not body.get('title'):
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Title is required',
                    'message': 'Task title cannot be empty'
                })
            }
        
        # Generate task ID and timestamps
        task_id = str(uuid.uuid4())
        current_time = datetime.utcnow().isoformat() + 'Z'
        
        # Create task item
        task_item = {
            'PK': f'TENANT#{tenant_id}',
            'SK': f'TASK#{task_id}',
            'GSI1PK': f'TENANT#{tenant_id}',
            'GSI1SK': f'STATUS#{body.get("status", "OPEN")}#{current_time}',
            'task_id': task_id,
            'tenant_id': tenant_id,
            'title': body['title'],
            'description': body.get('description', ''),
            'status': body.get('status', 'OPEN'),
            'priority': body.get('priority', 'MEDIUM'),
            'assigned_to': body.get('assigned_to', ''),
            'created_by': user_id,
            'created_at': current_time,
            'updated_at': current_time,
            'entity_type': 'TASK'
        }
        
        # Save to DynamoDB
        table.put_item(Item=task_item)
        
        logger.info(f"Task created: {task_id} for tenant: {tenant_id}")
        
        # Publish event to EventBridge
        event_detail = {
            'task_id': task_id,
            'tenant_id': tenant_id,
            'title': task_item['title'],
            'created_by': user_id,
            'created_at': current_time
        }
        
        eventbridge.put_events(
            Entries=[
                {
                    'Source': 'saas.tasks',
                    'DetailType': 'Task Created',
                    'Detail': json.dumps(event_detail),
                    'EventBusName': EVENT_BUS_NAME
                }
            ]
        )
        
        logger.info(f"TaskCreated event published for task: {task_id}")
        
        # Prepare response (exclude internal DynamoDB fields)
        response_task = {
            'task_id': task_item['task_id'],
            'tenant_id': task_item['tenant_id'],
            'title': task_item['title'],
            'description': task_item['description'],
            'status': task_item['status'],
            'priority': task_item['priority'],
            'assigned_to': task_item['assigned_to'],
            'created_by': task_item['created_by'],
            'created_at': task_item['created_at'],
            'updated_at': task_item['updated_at']
        }
        
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_task)
        }
        
    except KeyError as e:
        logger.error(f"Missing required field: {str(e)}")
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Bad Request',
                'message': f'Missing required field: {str(e)}'
            })
        }
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Invalid JSON',
                'message': 'Request body must be valid JSON'
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error creating task: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'Failed to create task'
            })
        }