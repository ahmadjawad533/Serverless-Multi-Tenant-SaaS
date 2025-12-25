"""
Update Task Lambda Function
Handles PUT /tasks/{id} endpoint for updating existing tasks
"""

import json
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
from typing import Dict, Any
import os
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))

# AWS clients
dynamodb = boto3.resource('dynamodb')

# Environment variables
TABLE_NAME = os.getenv('DYNAMODB_TABLE_NAME')

table = dynamodb.Table(TABLE_NAME)


def handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda handler for updating tasks
    
    Path parameters:
    - id: Task ID to update
    
    Body can contain:
    - title, description, status, priority, assigned_to
    """
    try:
        # Extract tenant context from authorizer
        authorizer = event['requestContext']['authorizer']
        tenant_id = authorizer['tenant_id']
        user_id = authorizer['user_id']
        user_role = authorizer['role']
        
        # Extract task ID from path
        task_id = event['pathParameters']['id']
        
        # Parse request body
        body = json.loads(event['body'])
        
        logger.info(f"Updating task: {task_id} for tenant: {tenant_id}")
        
        # First, get the existing task to verify ownership and existence
        existing_task_response = table.get_item(
            Key={
                'PK': f'TENANT#{tenant_id}',
                'SK': f'TASK#{task_id}'
            }
        )
        
        if 'Item' not in existing_task_response:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Task Not Found',
                    'message': f'Task {task_id} not found for tenant {tenant_id}'
                })
            }
        
        existing_task = existing_task_response['Item']
        
        # Check permissions - members can only update their own tasks
        if user_role == 'MEMBER' and existing_task.get('created_by') != user_id:
            return {
                'statusCode': 403,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Forbidden',
                    'message': 'Members can only update their own tasks'
                })
            }
        
        # Prepare update expression
        update_expression = "SET updated_at = :updated_at"
        expression_values = {
            ':updated_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Build update expression for allowed fields
        updatable_fields = ['title', 'description', 'status', 'priority', 'assigned_to']
        
        for field in updatable_fields:
            if field in body:
                update_expression += f", {field} = :{field}"
                expression_values[f':{field}'] = body[field]
        
        # Update GSI1SK if status is being changed
        if 'status' in body:
            update_expression += ", GSI1SK = :gsi1sk"
            expression_values[':gsi1sk'] = f"STATUS#{body['status']}#{expression_values[':updated_at']}"
        
        # Perform the update
        response = table.update_item(
            Key={
                'PK': f'TENANT#{tenant_id}',
                'SK': f'TASK#{task_id}'
            },
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )
        
        updated_task = response['Attributes']
        
        logger.info(f"Task updated: {task_id} for tenant: {tenant_id}")
        
        # Prepare response (exclude internal DynamoDB fields)
        response_task = {
            'task_id': updated_task['task_id'],
            'tenant_id': updated_task['tenant_id'],
            'title': updated_task['title'],
            'description': updated_task.get('description', ''),
            'status': updated_task['status'],
            'priority': updated_task.get('priority', 'MEDIUM'),
            'assigned_to': updated_task.get('assigned_to', ''),
            'created_by': updated_task.get('created_by', ''),
            'created_at': updated_task['created_at'],
            'updated_at': updated_task['updated_at']
        }
        
        return {
            'statusCode': 200,
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
        logger.error(f"Unexpected error updating task: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'Failed to update task'
            })
        }