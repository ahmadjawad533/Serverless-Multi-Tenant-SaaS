"""
Common utilities for Lambda functions
Shared functions for validation, formatting, and error handling
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger()


def generate_response(
    status_code: int,
    body: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Generate standardized API Gateway response"""
    
    default_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
    
    if headers:
        default_headers.update(headers)
    
    return {
        'statusCode': status_code,
        'headers': default_headers,
        'body': json.dumps(body, default=str)
    }


def generate_error_response(
    status_code: int,
    error_type: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generate standardized error response"""
    
    error_body = {
        'error': error_type,
        'message': message,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    if details:
        error_body['details'] = details
    
    return generate_response(status_code, error_body)


def validate_required_fields(data: Dict[str, Any], required_fields: list) -> Optional[str]:
    """Validate that all required fields are present in data"""
    
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            missing_fields.append(field)
    
    if missing_fields:
        return f"Missing required fields: {', '.join(missing_fields)}"
    
    return None


def validate_task_data(task_data: Dict[str, Any]) -> Optional[str]:
    """Validate task data structure and values"""
    
    # Check required fields
    required_fields = ['title']
    validation_error = validate_required_fields(task_data, required_fields)
    if validation_error:
        return validation_error
    
    # Validate title length
    title = task_data.get('title', '')
    if len(title) > 200:
        return "Title cannot exceed 200 characters"
    
    # Validate description length
    description = task_data.get('description', '')
    if len(description) > 1000:
        return "Description cannot exceed 1000 characters"
    
    # Validate status
    valid_statuses = ['OPEN', 'IN_PROGRESS', 'DONE', 'CANCELLED']
    status = task_data.get('status', 'OPEN')
    if status not in valid_statuses:
        return f"Status must be one of: {', '.join(valid_statuses)}"
    
    # Validate priority
    valid_priorities = ['LOW', 'MEDIUM', 'HIGH', 'URGENT']
    priority = task_data.get('priority', 'MEDIUM')
    if priority not in valid_priorities:
        return f"Priority must be one of: {', '.join(valid_priorities)}"
    
    return None


def extract_tenant_context(event: Dict[str, Any]) -> Dict[str, str]:
    """Extract tenant context from API Gateway event"""
    
    try:
        authorizer = event['requestContext']['authorizer']
        return {
            'tenant_id': authorizer['tenant_id'],
            'user_id': authorizer['user_id'],
            'role': authorizer['role'],
            'email': authorizer.get('email', '')
        }
    except KeyError as e:
        raise ValueError(f"Missing authorization context: {str(e)}")


def generate_task_id() -> str:
    """Generate unique task ID"""
    return str(uuid.uuid4())


def get_current_timestamp() -> str:
    """Get current UTC timestamp in ISO format"""
    return datetime.utcnow().isoformat() + 'Z'


def sanitize_task_for_response(task_item: Dict[str, Any]) -> Dict[str, Any]:
    """Remove internal DynamoDB fields from task item for API response"""
    
    return {
        'task_id': task_item.get('task_id'),
        'tenant_id': task_item.get('tenant_id'),
        'title': task_item.get('title'),
        'description': task_item.get('description', ''),
        'status': task_item.get('status'),
        'priority': task_item.get('priority', 'MEDIUM'),
        'assigned_to': task_item.get('assigned_to', ''),
        'created_by': task_item.get('created_by', ''),
        'created_at': task_item.get('created_at'),
        'updated_at': task_item.get('updated_at')
    }


def check_user_permissions(
    user_role: str,
    action: str,
    resource_owner: Optional[str] = None,
    current_user: Optional[str] = None
) -> bool:
    """Check if user has permission to perform action"""
    
    # Admins can do everything
    if user_role == 'ADMIN':
        return True
    
    # Members have limited permissions
    if user_role == 'MEMBER':
        if action in ['create', 'read']:
            return True
        elif action in ['update'] and resource_owner == current_user:
            return True
        elif action == 'delete':
            return False  # Only admins can delete
    
    return False


def log_api_request(event: Dict[str, Any], context: Dict[str, str]):
    """Log API request for monitoring and debugging"""
    
    request_info = {
        'method': event.get('httpMethod'),
        'path': event.get('path'),
        'tenant_id': context.get('tenant_id'),
        'user_id': context.get('user_id'),
        'user_agent': event.get('headers', {}).get('User-Agent'),
        'source_ip': event.get('requestContext', {}).get('identity', {}).get('sourceIp')
    }
    
    logger.info(f"API Request: {json.dumps(request_info)}")


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class PermissionError(Exception):
    """Custom exception for permission errors"""
    pass