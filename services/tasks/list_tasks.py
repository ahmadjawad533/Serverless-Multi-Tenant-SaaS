"""
List Tasks Lambda Function
Handles GET /tasks endpoint for retrieving tenant tasks
"""

import json
import boto3
from boto3.dynamodb.conditions import Key
from typing import Dict, Any, List
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
    Lambda handler for listing tasks
    
    Query parameters supported:
    - status: Filter by task status (OPEN, DONE)
    - limit: Maximum number of tasks to return
    - last_key: For pagination
    """
    try:
        # Extract tenant context from authorizer
        authorizer = event['requestContext']['authorizer']
        tenant_id = authorizer['tenant_id']
        user_id = authorizer['user_id']
        user_role = authorizer['role']
        
        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        status_filter = query_params.get('status')
        limit = int(query_params.get('limit', 50))
        last_key_param = query_params.get('last_key')
        
        # Validate limit
        if limit > 100:
            limit = 100
        
        logger.info(f"Listing tasks for tenant: {tenant_id}, status: {status_filter}")
        
        # Build query parameters
        query_kwargs = {
            'KeyConditionExpression': Key('PK').eq(f'TENANT#{tenant_id}') & 
                                    Key('SK').begins_with('TASK#'),
            'Limit': limit,
            'ScanIndexForward': False  # Most recent first
        }
        
        # Add pagination if provided
        if last_key_param:
            try:
                last_key = json.loads(last_key_param)
                query_kwargs['ExclusiveStartKey'] = last_key
            except json.JSONDecodeError:
                logger.warning(f"Invalid last_key parameter: {last_key_param}")
        
        # Query DynamoDB
        if status_filter:
            # Use GSI for status filtering
            query_kwargs.update({
                'IndexName': 'GSI1',
                'KeyConditionExpression': Key('GSI1PK').eq(f'TENANT#{tenant_id}') & 
                                        Key('GSI1SK').begins_with(f'STATUS#{status_filter}#')
            })
        
        response = table.query(**query_kwargs)
        
        # Process tasks
        tasks = []
        for item in response['Items']:
            # Only include task entities
            if item.get('entity_type') == 'TASK':
                task = {
                    'task_id': item['task_id'],
                    'tenant_id': item['tenant_id'],
                    'title': item['title'],
                    'description': item.get('description', ''),
                    'status': item['status'],
                    'priority': item.get('priority', 'MEDIUM'),
                    'assigned_to': item.get('assigned_to', ''),
                    'created_by': item.get('created_by', ''),
                    'created_at': item['created_at'],
                    'updated_at': item['updated_at']
                }
                tasks.append(task)
        
        # Prepare pagination info
        pagination = {
            'count': len(tasks),
            'has_more': 'LastEvaluatedKey' in response
        }
        
        if 'LastEvaluatedKey' in response:
            pagination['last_key'] = json.dumps(response['LastEvaluatedKey'])
        
        logger.info(f"Retrieved {len(tasks)} tasks for tenant: {tenant_id}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'tasks': tasks,
                'pagination': pagination,
                'filters': {
                    'status': status_filter,
                    'tenant_id': tenant_id
                }
            })
        }
        
    except ValueError as e:
        logger.error(f"Invalid parameter: {str(e)}")
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Bad Request',
                'message': f'Invalid parameter: {str(e)}'
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error listing tasks: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'Failed to retrieve tasks'
            })
        }