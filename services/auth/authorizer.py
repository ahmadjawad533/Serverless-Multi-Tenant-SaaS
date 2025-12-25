"""
Lambda Authorizer for JWT Token Validation
Validates Cognito JWT tokens and extracts tenant context
"""

import json
import jwt
import requests
from typing import Dict, Any
import os
import logging
from functools import lru_cache

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))

# Environment variables
USER_POOL_ID = os.getenv('USER_POOL_ID')
REGION = os.getenv('AWS_REGION', 'us-east-1')

# Cognito JWKS URL
JWKS_URL = f'https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json'


@lru_cache(maxsize=1)
def get_jwks():
    """Fetch and cache Cognito JWKS"""
    try:
        response = requests.get(JWKS_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch JWKS: {str(e)}")
        raise


def get_public_key(token_header):
    """Get the public key for token verification"""
    jwks = get_jwks()
    
    for key in jwks['keys']:
        if key['kid'] == token_header['kid']:
            return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
    
    raise ValueError("Public key not found")


def verify_token(token: str) -> Dict[str, Any]:
    """Verify JWT token and return claims"""
    try:
        # Decode header to get key ID
        unverified_header = jwt.get_unverified_header(token)
        
        # Get public key
        public_key = get_public_key(unverified_header)
        
        # Verify and decode token
        claims = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            audience=None,  # We'll validate this manually if needed
            options={"verify_aud": False}  # Disable audience verification for now
        )
        
        return claims
        
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {str(e)}")


def extract_tenant_context(claims: Dict[str, Any]) -> Dict[str, str]:
    """Extract tenant information from JWT claims"""
    
    # In a real implementation, tenant_id might come from:
    # 1. Custom claims in the JWT
    # 2. User attributes in Cognito
    # 3. A separate lookup based on user_id
    
    # For this demo, we'll extract from custom claims or use a default
    tenant_id = claims.get('custom:tenant_id', 'karachi-tech')  # Default for demo
    user_id = claims.get('sub')  # Cognito user ID
    email = claims.get('email', '')
    
    # Role could come from Cognito groups or custom claims
    role = claims.get('custom:role', 'MEMBER')  # Default role
    
    # If user is in Cognito groups, extract role from there
    cognito_groups = claims.get('cognito:groups', [])
    if 'Administrators' in cognito_groups:
        role = 'ADMIN'
    elif 'Members' in cognito_groups:
        role = 'MEMBER'
    
    return {
        'tenant_id': tenant_id,
        'user_id': user_id,
        'email': email,
        'role': role
    }


def generate_policy(effect: str, resource: str, context: Dict[str, str] = None) -> Dict[str, Any]:
    """Generate IAM policy for API Gateway"""
    policy = {
        'principalId': context.get('user_id', 'unknown') if context else 'unknown',
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource
                }
            ]
        }
    }
    
    if context:
        policy['context'] = context
    
    return policy


def handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda authorizer handler
    
    Expected event structure:
    {
        "authorizationToken": "Bearer <jwt_token>",
        "methodArn": "arn:aws:execute-api:region:account:api-id/stage/method/resource"
    }
    """
    try:
        # Extract token from Authorization header
        auth_token = event.get('authorizationToken', '')
        
        if not auth_token.startswith('Bearer '):
            logger.warning("Invalid authorization header format")
            raise ValueError("Invalid authorization header")
        
        # Extract JWT token
        jwt_token = auth_token.replace('Bearer ', '')
        
        # Verify token and get claims
        claims = verify_token(jwt_token)
        
        # Extract tenant context
        tenant_context = extract_tenant_context(claims)
        
        logger.info(f"Authorized user: {tenant_context['user_id']} for tenant: {tenant_context['tenant_id']}")
        
        # Generate allow policy with context
        return generate_policy('Allow', event['methodArn'], tenant_context)
        
    except ValueError as e:
        logger.warning(f"Authorization failed: {str(e)}")
        # Return deny policy
        return generate_policy('Deny', event['methodArn'])
        
    except Exception as e:
        logger.error(f"Unexpected error in authorizer: {str(e)}")
        # Return deny policy for any unexpected errors
        return generate_policy('Deny', event['methodArn'])