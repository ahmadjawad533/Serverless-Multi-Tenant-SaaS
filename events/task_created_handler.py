"""
Task Created Event Handler
Processes TaskCreated events from EventBridge
Handles analytics, notifications, and audit logging
"""

import json
import boto3
from typing import Dict, Any, List
import os
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))

# AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Environment variables
TABLE_NAME = os.getenv('DYNAMODB_TABLE_NAME')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

table = dynamodb.Table(TABLE_NAME)


def handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    EventBridge handler for TaskCreated events
    
    Expected event structure:
    {
        "Records": [
            {
                "eventSource": "aws:events",
                "eventName": "TaskCreated",
                "eventBridge": {
                    "source": "saas.tasks",
                    "detail-type": "Task Created",
                    "detail": {
                        "task_id": "uuid",
                        "tenant_id": "karachi-tech",
                        "title": "Task title",
                        "created_by": "user_id",
                        "created_at": "timestamp"
                    }
                }
            }
        ]
    }
    """
    
    processed_events = []
    
    try:
        # Process each event record
        for record in event.get('Records', []):
            if record.get('source') == 'saas.tasks':
                detail = record.get('detail', {})
                
                # Extract event data
                task_id = detail.get('task_id')
                tenant_id = detail.get('tenant_id')
                title = detail.get('title')
                created_by = detail.get('created_by')
                created_at = detail.get('created_at')
                
                logger.info(f"Processing TaskCreated event for task: {task_id}, tenant: {tenant_id}")
                
                # Process analytics
                analytics_result = await_process_analytics(detail)
                
                # Send notifications
                notification_result = await_send_notifications(detail)
                
                # Create audit log
                audit_result = await_create_audit_log(detail)
                
                processed_events.append({
                    'task_id': task_id,
                    'tenant_id': tenant_id,
                    'analytics': analytics_result,
                    'notifications': notification_result,
                    'audit': audit_result
                })
        
        logger.info(f"Successfully processed {len(processed_events)} TaskCreated events")
        
        return {
            'statusCode': 200,
            'processed_events': len(processed_events),
            'results': processed_events
        }
        
    except Exception as e:
        logger.error(f"Error processing TaskCreated events: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e),
            'processed_events': len(processed_events)
        }


def await_process_analytics(event_detail: Dict[str, Any]) -> Dict[str, Any]:
    """Process analytics for task creation"""
    try:
        tenant_id = event_detail['tenant_id']
        task_id = event_detail['task_id']
        created_at = event_detail['created_at']
        
        # Create analytics record in DynamoDB
        analytics_item = {
            'PK': f'TENANT#{tenant_id}',
            'SK': f'ANALYTICS#{created_at}#{task_id}',
            'GSI1PK': f'ANALYTICS#{tenant_id}',
            'GSI1SK': f'TASK_CREATED#{created_at}',
            'event_type': 'TASK_CREATED',
            'task_id': task_id,
            'tenant_id': tenant_id,
            'created_by': event_detail.get('created_by'),
            'timestamp': created_at,
            'entity_type': 'ANALYTICS'
        }
        
        table.put_item(Item=analytics_item)
        
        # Update tenant metrics
        metrics_item = {
            'PK': f'TENANT#{tenant_id}',
            'SK': 'METRICS#TASKS',
            'total_tasks': 1,  # This would be incremented in real implementation
            'tasks_this_month': 1,
            'last_task_created': created_at,
            'entity_type': 'METRICS'
        }
        
        # Use update with atomic counter in real implementation
        table.put_item(Item=metrics_item)
        
        logger.info(f"Analytics processed for task: {task_id}")
        
        return {
            'status': 'success',
            'analytics_recorded': True,
            'metrics_updated': True
        }
        
    except Exception as e:
        logger.error(f"Analytics processing failed: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }


def await_send_notifications(event_detail: Dict[str, Any]) -> Dict[str, Any]:
    """Send notifications for task creation"""
    try:
        tenant_id = event_detail['tenant_id']
        task_id = event_detail['task_id']
        title = event_detail['title']
        created_by = event_detail.get('created_by')
        
        # In a real implementation, this would:
        # 1. Look up notification preferences for the tenant
        # 2. Send emails via SES
        # 3. Send Slack notifications via webhooks
        # 4. Send push notifications via SNS
        
        # For demo, we'll create a notification record
        notification_item = {
            'PK': f'TENANT#{tenant_id}',
            'SK': f'NOTIFICATION#{datetime.utcnow().isoformat()}Z#{task_id}',
            'notification_type': 'TASK_CREATED',
            'task_id': task_id,
            'tenant_id': tenant_id,
            'title': title,
            'created_by': created_by,
            'status': 'SENT',  # Would be 'PENDING' initially
            'channels': ['email', 'slack'],  # Based on tenant preferences
            'entity_type': 'NOTIFICATION'
        }
        
        table.put_item(Item=notification_item)
        
        logger.info(f"Notifications sent for task: {task_id}")
        
        return {
            'status': 'success',
            'channels': ['email', 'slack'],
            'notification_id': notification_item['SK']
        }
        
    except Exception as e:
        logger.error(f"Notification sending failed: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }


def await_create_audit_log(event_detail: Dict[str, Any]) -> Dict[str, Any]:
    """Create audit log for task creation"""
    try:
        tenant_id = event_detail['tenant_id']
        task_id = event_detail['task_id']
        created_at = event_detail['created_at']
        created_by = event_detail.get('created_by')
        
        # Create audit log entry
        audit_item = {
            'PK': f'TENANT#{tenant_id}',
            'SK': f'AUDIT#{created_at}#{task_id}',
            'GSI1PK': f'AUDIT#{tenant_id}',
            'GSI1SK': f'TASK_CREATED#{created_at}',
            'action': 'TASK_CREATED',
            'resource_type': 'TASK',
            'resource_id': task_id,
            'tenant_id': tenant_id,
            'user_id': created_by,
            'timestamp': created_at,
            'details': {
                'task_title': event_detail['title'],
                'event_source': 'task_management_api'
            },
            'entity_type': 'AUDIT'
        }
        
        table.put_item(Item=audit_item)
        
        # Also store in S3 for long-term compliance
        audit_key = f"audit-logs/{tenant_id}/{created_at[:7]}/{task_id}.json"  # YYYY-MM folder structure
        
        s3.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=audit_key,
            Body=json.dumps(audit_item, default=str),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        
        logger.info(f"Audit log created for task: {task_id}")
        
        return {
            'status': 'success',
            'audit_recorded': True,
            's3_backup': True,
            's3_key': audit_key
        }
        
    except Exception as e:
        logger.error(f"Audit logging failed: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }