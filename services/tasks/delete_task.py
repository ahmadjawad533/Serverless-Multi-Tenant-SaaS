"""
Delete Task Lambda Function
Handles DELETE /tasks/{id} endpoint for deleting tasks
Only ADMIN users can delete tasks
"""

import json
import boto3
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
    Lambda handler for deleting tasks
    
    Path parameters:
    - id: Task ID to delete
    
    Only ADMIN users can delete tasks
    """
    try:
        # Extract tenant context from authorizer
        authorizer = event['requestContext']['authorizer']
        tenant_id = authorizer['tenant_id']
        user_id = authorizer['user_id']
        user_role = authorizer['role']
        
        # Extract task ID from path
        task_id = event['pathParameters']['id']
        
        logger.info(f"Delete request for task: {task_id} by user: {user_id} (role: {user_role})")
        
        # Check permissions - only ADMINs can delete tasks
        if user_role != 'ADMIN':
            return {
                'statusCode': 403,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Forbidden',
                    'message': 'Only administrators can delete tasks'
                })
            }
        
        # First, verify the task exists and belongs to the tenant
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
        
        # Delete the task
        table.delete_item(
            Key={
                'PK': f'TENANT#{tenant_id}',
                'SK': f'TASK#{task_id}'
            }
        )
        
        logger.info(f"Task deleted: {task_id} for tenant: {tenant_id} by admin: {user_id}")
        
        # Return success response with deleted task info
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Task deleted successfully',
                'deleted_task': {
                    'task_id': task_id,
                    'tenant_id': tenant_id,
                    'title': existing_task.get('title', ''),
                    'deleted_by': user_id,
                    'deleted_at': existing_task.get('updated_at', '')
                }
            })
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
        
    except Exception as e:
        logger.error(f"Unexpected error deleting task: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'Failed to delete task'
            })
        }