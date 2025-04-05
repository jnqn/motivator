import json
import os
import boto3
import base64
from botocore.exceptions import ClientError
import logging

from src.main import process_activities

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_secret():
    """Retrieve secrets from AWS Secrets Manager"""
    secret_name = os.environ.get('SECRET_NAME')
    region_name = os.environ.get('AWS_REGION', 'us-east-1')
    
    if not secret_name:
        raise ValueError('SECRET_NAME environment variable must be set')
    
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        logger.error(f"Error retrieving secret: {str(e)}")
        raise e

    # Decrypts secret using the associated KMS key
    if 'SecretString' in get_secret_value_response:
        secret = json.loads(get_secret_value_response['SecretString'])
    else:
        secret = json.loads(base64.b64decode(get_secret_value_response['SecretBinary']))
    
    # Set environment variables from the secret
    for key, value in secret.items():
        os.environ[key] = value


def lambda_handler(event, context):
    """AWS Lambda handler function - runs on a schedule"""
    try:
        logger.info("Starting Motivator scheduled run")
        
        # Load secrets
        get_secret()
        
        # Get parameters from environment variables with defaults
        create_playlist = os.environ.get('CREATE_PLAYLIST', 'true').lower() == 'true'
        limit = int(os.environ.get('ACTIVITY_LIMIT', 1))
        
        # In Lambda, we always use S3 for token storage
        use_s3 = True
        
        # Verify S3 bucket is configured
        s3_bucket = os.environ.get('S3_BUCKET')
        if not s3_bucket:
            logger.error("S3_BUCKET environment variable must be set")
            raise ValueError("S3_BUCKET environment variable must be set")
            
        logger.info(f"Processing with create_playlist={create_playlist}, limit={limit}, s3_bucket={s3_bucket}")
        
        # Process activities
        results = process_activities(
            create_playlist=create_playlist, 
            limit=limit,
            use_s3=use_s3
        )
        
        logger.info(f"Successfully processed {len(results)} activities")
        return {
            'success': True,
            'activities': results
        }
    except Exception as e:
        logger.error(f"Error running Motivator: {str(e)}")
        raise