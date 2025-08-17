#!/usr/bin/env python3
"""
Simple Lambda function to test downloading NSW premises list

This minimal version:
1. Calculates the previous month (where data should be available)
2. Downloads the CSV file from NSW government
3. Saves to S3
4. Returns success/failure

Environment Variables Required:
- S3_BUCKET: S3 bucket name for storing the downloaded file
"""

import json
import logging
from datetime import datetime, timedelta

import boto3
import requests

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS client
s3_client = boto3.client('s3')


def get_previous_month():
    """
    Get the previous month (where data should be available)
    """
    now = datetime.now()
    # Go back one month
    if now.month == 1:
        previous_month = datetime(now.year - 1, 12, 1)
    else:
        previous_month = datetime(now.year, now.month - 1, 1)
    
    return previous_month


def download_premises_list(target_month):
    """
    Download NSW premises list for a specific month
    """
    base_url = "https://www.liquorandgaming.nsw.gov.au/documents/liquor-licence/"
    
    # Try different filename formats NSW might use
    month_formats = [
        target_month.strftime("%b").lower(),           # "jul"
        target_month.strftime("%B").lower(),           # "july"  
        f"{target_month.strftime('%b').lower()}-{target_month.year}",  # "jul-2025"
        target_month.strftime("%m"),                   # "07"
        f"{target_month.strftime('%b')}-{target_month.year}",          # "Jul-2025"
        f"{target_month.strftime('%B')}-{target_month.year}",          # "July-2025"
    ]
    
    logger.info(f"Attempting to download premises list for {target_month.strftime('%B %Y')}")
    
    for month_format in month_formats:
        filename = f"premises-list-{month_format}.csv"
        url = f"{base_url}{filename}"
        
        try:
            logger.info(f"Trying: {url}")
            
            # Test if file exists first
            response = requests.head(url, timeout=10)
            if response.status_code != 200:
                logger.info(f"File not available: {filename} (status: {response.status_code})")
                continue
            
            # Download the file
            logger.info(f"File found! Downloading: {filename}")
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            
            # Save to /tmp
            local_path = f"/tmp/{filename}"
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            file_size = len(response.content)
            logger.info(f"Successfully downloaded: {filename} ({file_size:,} bytes)")
            
            return local_path, filename, url
            
        except Exception as e:
            logger.warning(f"Failed to download {filename}: {e}")
            continue
    
    raise Exception(f"Could not download premises list for {target_month.strftime('%B %Y')}. Tried all common formats.")


def upload_to_s3(local_file_path, filename, s3_bucket):
    """
    Upload downloaded file to S3
    """
    try:
        s3_key = f"premises_data/{filename}"
        
        logger.info(f"Uploading to S3: s3://{s3_bucket}/{s3_key}")
        s3_client.upload_file(local_file_path, s3_bucket, s3_key)
        
        logger.info(f"Successfully uploaded to S3: {s3_key}")
        return s3_key
        
    except Exception as e:
        logger.error(f"Failed to upload to S3: {e}")
        raise


def lambda_handler(event, context):
    """
    Main Lambda handler - test download functionality
    """
    try:
        logger.info("Starting NSW premises list download test...")
        
        # Get environment variables
        s3_bucket = event.get('s3_bucket') or context.get('s3_bucket') or 'your-default-bucket'
        
        # Calculate target month (previous month)
        target_month = get_previous_month()
        logger.info(f"Target month: {target_month.strftime('%B %Y')}")
        
        # Download the file
        local_path, filename, download_url = download_premises_list(target_month)
        
        # Upload to S3
        s3_key = upload_to_s3(local_path, filename, s3_bucket)
        
        # Success response
        result = {
            'status': 'success',
            'message': 'NSW premises list downloaded successfully',
            'details': {
                'month': target_month.strftime('%B %Y'),
                'filename': filename,
                'download_url': download_url,
                's3_location': f's3://{s3_bucket}/{s3_key}',
                'local_path': local_path
            }
        }
        
        logger.info("Download test completed successfully!")
        logger.info(f"File saved to: s3://{s3_bucket}/{s3_key}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result, indent=2)
        }
        
    except Exception as e:
        error_msg = f"Download test failed: {str(e)}"
        logger.error(error_msg)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'message': error_msg
            })
        }


# For local testing
if __name__ == "__main__":
    # Mock Lambda context for local testing
    class MockContext:
        def __init__(self):
            self.function_name = 'test-download'
            self.memory_limit_in_mb = 128
    
    # Test event
    test_event = {
        's3_bucket': 'test-bucket-name'
    }
    
    # Run test
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
