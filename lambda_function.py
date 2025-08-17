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
import os
from datetime import datetime, timedelta

import boto3
import pandas as pd
import requests

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS client
s3_client = boto3.client('s3')


def get_target_months():
    """
    Get the current month and previous month for comparison
    """
    now = datetime.now()
    
    # Current month (July 2025 in this case)
    current_month = datetime(now.year, now.month - 1, 1)  # July
    
    # Previous month (June 2025)
    if current_month.month == 1:
        previous_month = datetime(current_month.year - 1, 12, 1)
    else:
        previous_month = datetime(current_month.year, current_month.month - 1, 1)
    
    return current_month, previous_month


def scrape_premises_list_urls():
    """
    Scrape the NSW Liquor and Gaming website to get actual download URLs
    """
    import re
    
    premises_page_url = "https://www.liquorandgaming.nsw.gov.au/resources/licensed-premises-data"
    
    try:
        logger.info(f"Scraping premises list URLs from: {premises_page_url}")
        
        # Get the premises data page
        response = requests.get(premises_page_url, timeout=30)
        response.raise_for_status()
        
        # Find all Excel file links in the HTML
        # Pattern: href="/__data/assets/excel_doc/.../premises-list-Mon-YYYY.xlsx"
        pattern = r'href="([^"]*premises-list-[^"]*\.xlsx)"'
        matches = re.findall(pattern, response.text)
        
        # Build a dictionary of month/year -> URL
        urls = {}
        for match in matches:
            # Make sure it's a full URL
            if match.startswith('/'):
                full_url = f"https://www.liquorandgaming.nsw.gov.au{match}"
            else:
                full_url = match
            
            # Extract month and year from filename
            # Pattern: premises-list-Jul-2025.xlsx
            filename_pattern = r'premises-list-([A-Za-z]+)-(\d{4})\.xlsx'
            filename_match = re.search(filename_pattern, full_url)
            
            if filename_match:
                month_str = filename_match.group(1)
                year_int = int(filename_match.group(2))
                urls[(month_str, year_int)] = full_url
                logger.info(f"Found: {month_str} {year_int} -> {full_url}")
        
        logger.info(f"Successfully scraped {len(urls)} premises list URLs")
        return urls
        
    except Exception as e:
        logger.error(f"Failed to scrape premises list URLs: {e}")
        return {}





def download_premises_list(target_month):
    """
    Download NSW premises list for a specific month by scraping the website for actual URLs
    """
    logger.info(f"Attempting to download premises list for {target_month.strftime('%B %Y')}")
    
    month_key = (target_month.strftime('%b'), target_month.year)
    
    # Scrape the website to get real URLs
    logger.info("Scraping NSW website for current download URLs...")
    scraped_urls = scrape_premises_list_urls()
    
    if month_key in scraped_urls:
        url = scraped_urls[month_key]
        filename = url.split('/')[-1]  # Extract filename from URL
        
        logger.info(f"Found scraped URL: {url}")
        if try_download_file(url, filename, target_month):
            return f"/tmp/{filename}", filename, url
    
    raise Exception(f"Could not download premises list for {target_month.strftime('%B %Y')}. Not found via scraping.")


def try_download_file(url, filename, target_month):
    """
    Try to download a file from a specific URL
    """
    try:
        logger.info(f"Trying: {url}")
        
        # Test if file exists first
        response = requests.head(url, timeout=15)
        if response.status_code != 200:
            logger.info(f"File not available: {filename} (status: {response.status_code})")
            return False
        
        # Download the file
        logger.info(f"File found! Downloading: {filename}")
        response = requests.get(url, timeout=90)
        response.raise_for_status()
        
        # Save to /tmp
        local_path = f"/tmp/{filename}"
        with open(local_path, 'wb') as f:
            f.write(response.content)
        
        file_size = len(response.content)
        logger.info(f"Successfully downloaded: {filename} ({file_size:,} bytes)")
        
        return True
        
    except Exception as e:
        logger.warning(f"Failed to download {filename}: {e}")
        return False


def check_file_exists_in_s3(filename, s3_bucket):
    """
    Check if a file already exists in S3
    """
    try:
        s3_key = f"premises_data/{filename}"
        s3_client.head_object(Bucket=s3_bucket, Key=s3_key)
        logger.info(f"File already exists in S3: s3://{s3_bucket}/{s3_key}")
        return True, s3_key
    except:
        logger.info(f"File not found in S3: {filename}")
        return False, None


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


def get_or_download_file(target_month, s3_bucket):
    """
    Get file from S3 if it exists, otherwise download it
    """
    # Generate expected filename
    month_format = f"{target_month.strftime('%b')}-{target_month.year}"
    filename = f"premises-list-{month_format}.xlsx"
    
    # Check if file already exists in S3
    exists, s3_key = check_file_exists_in_s3(filename, s3_bucket)
    
    if exists:
        logger.info(f"Using existing file from S3: {filename}")
        return None, filename, f"s3://{s3_bucket}/{s3_key}", "existing"
    else:
        logger.info(f"File not in S3, downloading: {filename}")
        # Download the file
        local_path, filename, download_url = download_premises_list(target_month)
        # Upload to S3
        s3_key = upload_to_s3(local_path, filename, s3_bucket)
        return local_path, filename, f"s3://{s3_bucket}/{s3_key}", "downloaded"


def download_file_from_s3(filename, s3_bucket):
    """
    Download a file from S3 to local /tmp directory
    """
    try:
        s3_key = f"premises_data/{filename}"
        local_path = f"/tmp/{filename}"
        
        logger.info(f"Downloading from S3: s3://{s3_bucket}/{s3_key}")
        s3_client.download_file(s3_bucket, s3_key, local_path)
        
        logger.info(f"Successfully downloaded: {filename}")
        return local_path
        
    except Exception as e:
        logger.error(f"Failed to download from S3: {e}")
        raise


def filter_target_businesses(df):
    """
    Filter for target business types (restaurants, bars, hotels, etc.)
    """
    target_business_types = [
        'restaurant', 'bar', 'hotel', 'pub', 'cafe', 'club', 'brewery', 
        'distillery', 'winery', 'tavern', 'bistro', 'eatery', 'dining',
        'catering', 'food', 'drink', 'wine', 'beer', 'spirit'
    ]
    
    logger.info(f"Available columns: {list(df.columns)}")
    
    # Use the exact column names from NSW premises list
    business_type_col = 'Business type' if 'Business type' in df.columns else None
    trading_name_col = 'Licence name' if 'Licence name' in df.columns else None
    
    logger.info(f"Using business type column: {business_type_col}")
    logger.info(f"Using trading name column: {trading_name_col}")
    
    # Convert to lowercase for matching
    df_filtered = df.copy()
    
    # Create filter conditions based on available columns
    filters = []
    
    if business_type_col and business_type_col in df.columns:
        df_filtered['business_type_lower'] = df_filtered[business_type_col].astype(str).str.lower()
        business_type_match = df_filtered['business_type_lower'].str.contains('|'.join(target_business_types), na=False)
        filters.append(business_type_match)
        logger.info(f"Added business type filter from column: {business_type_col}")
    
    if trading_name_col and trading_name_col in df.columns:
        df_filtered['trading_name_lower'] = df_filtered[trading_name_col].astype(str).str.lower()
        trading_name_match = df_filtered['trading_name_lower'].str.contains('|'.join(target_business_types), na=False)
        filters.append(trading_name_match)
        logger.info(f"Added trading name filter from column: {trading_name_col}")
    
    # If no specific columns found, try all text columns
    if not filters:
        logger.info("No specific business type/trading name columns found, searching all text columns...")
        for col in df.columns:
            if df[col].dtype == 'object':  # Text columns
                col_lower_data = df[col].astype(str).str.lower()
                col_match = col_lower_data.str.contains('|'.join(target_business_types), na=False)
                if col_match.any():
                    filters.append(col_match)
                    logger.info(f"Found matches in column: {col}")
    
    # Apply filters
    if filters:
        # Combine all filters with OR
        combined_filter = filters[0]
        for f in filters[1:]:
            combined_filter = combined_filter | f
        
        filtered_df = df_filtered[combined_filter].copy()
    else:
        logger.warning("No target business filters could be applied - returning all records")
        filtered_df = df_filtered.copy()
    
    # Clean up helper columns but preserve original columns
    helper_columns = [col for col in df_filtered.columns if col.endswith('_lower') and col not in df.columns]
    if helper_columns:
        filtered_df = filtered_df.drop(helper_columns, axis=1, errors='ignore')
        logger.info(f"Removed helper columns: {helper_columns}")
    
    logger.info(f"Final filtered columns: {list(filtered_df.columns)}")
    
    logger.info(f"Filtered to {len(filtered_df)} target businesses from {len(df)} total")
    return filtered_df


def identify_new_businesses(current_month, previous_month, s3_bucket):
    """
    Compare current and previous month data to find new businesses
    """
    try:
        # Get file paths
        current_filename = f"premises-list-{current_month.strftime('%b')}-{current_month.year}.xlsx"
        previous_filename = f"premises-list-{previous_month.strftime('%b')}-{previous_month.year}.xlsx"
        
        # Download files from S3 if needed
        current_path = f"/tmp/{current_filename}"
        previous_path = f"/tmp/{previous_filename}"
        
        # Check if files exist locally, if not download from S3
        import os
        if not os.path.exists(current_path):
            current_path = download_file_from_s3(current_filename, s3_bucket)
        if not os.path.exists(previous_path):
            previous_path = download_file_from_s3(previous_filename, s3_bucket)
        
        logger.info("Loading current month data...")
        # Skip first 3 rows (empty, description, summary) and use row 4 as header
        current_df = pd.read_excel(current_path, header=3)
        logger.info(f"Current month: {len(current_df)} total records")
        logger.info(f"Current month columns: {list(current_df.columns)}")
        
        logger.info("Loading previous month data...")
        # Skip first 3 rows (empty, description, summary) and use row 4 as header
        previous_df = pd.read_excel(previous_path, header=3)
        logger.info(f"Previous month: {len(previous_df)} total records")
        logger.info(f"Previous month columns: {list(previous_df.columns)}")
        
        # Filter for target businesses
        current_filtered = filter_target_businesses(current_df)
        previous_filtered = filter_target_businesses(previous_df)
        
        # Find new businesses (in current but not in previous)
        # Use the exact license column name from NSW premises list  
        logger.info(f"Looking for license column in filtered data...")
        logger.info(f"Current filtered columns: {list(current_filtered.columns)}")
        logger.info(f"Previous filtered columns: {list(previous_filtered.columns)}")
        
        license_col = None
        for col in current_filtered.columns:
            if 'licence number' in col.lower() or 'license number' in col.lower():
                license_col = col
                break
        
        if not license_col:
            logger.error("Could not find license number column after filtering")
            logger.info(f"Available columns after filtering: {list(current_filtered.columns)}")
            # Try to find any column with 'licence' or 'license' in it
            possible_cols = [col for col in current_filtered.columns if 'licen' in col.lower()]
            logger.info(f"Columns containing 'licen': {possible_cols}")
            if possible_cols:
                license_col = possible_cols[0]
                logger.info(f"Using first available license column: {license_col}")
            else:
                raise Exception("License number column not found even after fallback search")
        
        logger.info(f"Using license column: {license_col}")
        
        # Use License Number as the unique identifier
        current_licenses = set(current_filtered[license_col].astype(str))
        previous_licenses = set(previous_filtered[license_col].astype(str))
        
        new_license_numbers = current_licenses - previous_licenses
        
        # Get the full records for new businesses
        new_businesses = current_filtered[
            current_filtered[license_col].astype(str).isin(new_license_numbers)
        ].copy()
        
        logger.info(f"Found {len(new_businesses)} new businesses")
        
        return new_businesses
        
    except Exception as e:
        logger.error(f"Failed to identify new businesses: {e}")
        raise


def format_for_airtable(new_businesses_df):
    """
    Convert NSW premises data to Airtable format
    """
    # Create the Airtable-formatted DataFrame
    airtable_df = pd.DataFrame()
    
    # Map NSW columns to Airtable columns
    airtable_df['Name'] = new_businesses_df.get('Licence name', '')
    airtable_df['Address'] = new_businesses_df.get('Address', '')
    airtable_df['Suburb'] = new_businesses_df.get('Suburb', '')
    airtable_df['Postcode'] = new_businesses_df.get('Postcode', '')
    airtable_df['LGA'] = new_businesses_df.get('LGA', '')
    airtable_df['Licensee'] = new_businesses_df.get('Licensee', '')
    airtable_df['Licensee ABN'] = new_businesses_df.get('Licensee ABN', '')
    
    # Empty columns for contact info (to be filled later)
    airtable_df['Facebook Link'] = ''
    airtable_df['Instagram link'] = ''
    airtable_df['Email Address'] = ''
    airtable_df['Phone Number'] = ''
    
    # Empty columns for tracking
    airtable_df['Date email 1 sent'] = ''
    airtable_df['Date email 2 sent'] = ''
    airtable_df['Date email 3 sent'] = ''
    
    # Notes with source info
    current_date = pd.Timestamp.now().strftime('%Y-%m-%d')
    airtable_df['Notes'] = f'New prospect from NSW premises list {current_date}'
    
    logger.info(f"Formatted {len(airtable_df)} businesses for Airtable")
    return airtable_df


def upload_to_airtable(airtable_df):
    """
    Upload new businesses to Airtable
    """
    try:
        # Get Airtable credentials from environment variables
        airtable_token = os.environ.get('AIRTABLE_TOKEN')
        airtable_base_id = os.environ.get('AIRTABLE_BASE_ID')
        airtable_table_name = os.environ.get('AIRTABLE_TABLE_NAME', 'Businesses')
        
        # Debug logging (mask sensitive parts)
        logger.info(f"Airtable token present: {bool(airtable_token)}")
        logger.info(f"Airtable token starts with: {airtable_token[:10] if airtable_token else 'None'}...")
        logger.info(f"Airtable base ID: {airtable_base_id}")
        logger.info(f"Airtable table name: {airtable_table_name}")
        
        if not airtable_token or not airtable_base_id:
            logger.warning("Airtable credentials not provided - skipping Airtable upload")
            return None
        
        logger.info(f"Uploading {len(airtable_df)} businesses to Airtable...")
        
        # Test connection first with a simple GET request
        test_url = f"https://api.airtable.com/v0/{airtable_base_id}/{airtable_table_name}?maxRecords=1"
        test_headers = {
            'Authorization': f'Bearer {airtable_token}',
        }
        
        logger.info(f"Testing connection with: {test_url}")
        test_response = requests.get(test_url, headers=test_headers)
        logger.info(f"Test response: {test_response.status_code} - {test_response.text[:200]}...")
        
        if test_response.status_code != 200:
            logger.error(f"Connection test failed: {test_response.status_code} - {test_response.text}")
            
            # Try to get list of tables to help debug
            schema_url = f"https://api.airtable.com/v0/meta/bases/{airtable_base_id}/tables"
            schema_response = requests.get(schema_url, headers=test_headers)
            logger.info(f"Schema response: {schema_response.status_code}")
            if schema_response.status_code == 200:
                tables = schema_response.json().get('tables', [])
                table_names = [table.get('name') for table in tables]
                logger.info(f"Available tables: {table_names}")
            else:
                logger.error(f"Failed to get schema: {schema_response.text}")
            
            return None
        
        # URL encode the table name in case it has spaces/special chars
        import urllib.parse
        encoded_table_name = urllib.parse.quote(airtable_table_name)
        
        # Airtable API endpoint for creating records
        url = f"https://api.airtable.com/v0/{airtable_base_id}/{encoded_table_name}"
        logger.info(f"Using encoded URL: {url}")
        
        headers = {
            'Authorization': f'Bearer {airtable_token}',
            'Content-Type': 'application/json'
        }
        
        # Convert DataFrame to Airtable records format
        records = []
        for _, row in airtable_df.iterrows():
            # Convert row to dict and remove empty values
            fields = {k: v for k, v in row.to_dict().items() if pd.notna(v) and v != ''}
            records.append({'fields': fields})
        
        # Airtable allows max 10 records per request
        uploaded_count = 0
        batch_size = 10
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            payload = {'records': batch}
            
            logger.info(f"Uploading batch {i//batch_size + 1} ({len(batch)} records)...")
            
            logger.info(f"Making request to: {url}")
            logger.info(f"Headers: {headers}")
            logger.info(f"Payload sample: {json.dumps(payload['records'][0] if payload['records'] else {}, indent=2)}")
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                uploaded_count += len(batch)
                logger.info(f"Successfully uploaded batch ({len(batch)} records)")
            else:
                logger.error(f"Failed to upload batch: {response.status_code} - {response.text}")
                logger.error(f"Request URL: {url}")
                logger.error(f"Request headers: {headers}")
                # Continue with next batch rather than failing completely
        
        logger.info(f"Airtable upload complete: {uploaded_count}/{len(records)} records uploaded")
        return uploaded_count
        
    except Exception as e:
        logger.error(f"Failed to upload to Airtable: {e}")
        return None


def save_new_businesses_to_s3(new_businesses_df, current_month, s3_bucket):
    """
    Save new businesses as CSV to S3 in Airtable format and upload to Airtable
    """
    try:
        # Format data for Airtable
        airtable_formatted = format_for_airtable(new_businesses_df)
        
        # Create filename
        date_str = current_month.strftime('%Y-%m-%d')
        filename = f"new_businesses_{date_str}.csv"
        local_path = f"/tmp/{filename}"
        
        # Save to local file first (Airtable format)
        airtable_formatted.to_csv(local_path, index=False)
        logger.info(f"Saved {len(airtable_formatted)} new businesses to {filename} (Airtable format)")
        
        # Upload to S3 in new_businesses folder
        s3_key = f"new_businesses/{filename}"
        logger.info(f"Uploading to S3: s3://{s3_bucket}/{s3_key}")
        s3_client.upload_file(local_path, s3_bucket, s3_key)
        
        logger.info(f"Successfully uploaded to S3: {s3_key}")
        
        # Upload to Airtable
        airtable_count = upload_to_airtable(airtable_formatted)
        
        return s3_key, airtable_count
        
    except Exception as e:
        logger.error(f"Failed to save new businesses to S3: {e}")
        raise


def lambda_handler(event, context):
    """
    Main Lambda handler - test downloading both current and previous month files
    """
    try:
        logger.info("Starting NSW premises list monthly workflow...")
        
        # Get S3 bucket from environment variable or event
        s3_bucket = event.get('s3_bucket')
        if not s3_bucket:
            import os
            s3_bucket = os.environ.get('S3_BUCKET')
        
        if not s3_bucket:
            raise Exception("S3_BUCKET must be provided in event or environment variables")
        
        logger.info(f"Using S3 bucket: {s3_bucket}")
        
        # Get both months for comparison
        current_month, previous_month = get_target_months()
        logger.info(f"Current month: {current_month.strftime('%B %Y')}")
        logger.info(f"Previous month: {previous_month.strftime('%B %Y')}")
        
        # Get or download current month file
        logger.info("=" * 50)
        logger.info("PROCESSING CURRENT MONTH FILE")
        logger.info("=" * 50)
        current_local_path, current_filename, current_s3_location, current_status = get_or_download_file(current_month, s3_bucket)
        
        # Get or download previous month file
        logger.info("=" * 50)
        logger.info("PROCESSING PREVIOUS MONTH FILE")
        logger.info("=" * 50)
        previous_local_path, previous_filename, previous_s3_location, previous_status = get_or_download_file(previous_month, s3_bucket)
        
        # Identify new businesses
        logger.info("=" * 50)
        logger.info("IDENTIFYING NEW BUSINESSES")
        logger.info("=" * 50)
        new_businesses = identify_new_businesses(current_month, previous_month, s3_bucket)
        
        # Save new businesses to S3 and upload to Airtable
        new_businesses_s3_key = None
        airtable_upload_count = None
        if len(new_businesses) > 0:
            logger.info("=" * 50)
            logger.info("SAVING NEW BUSINESSES TO S3 & AIRTABLE")
            logger.info("=" * 50)
            new_businesses_s3_key, airtable_upload_count = save_new_businesses_to_s3(new_businesses, current_month, s3_bucket)
        else:
            logger.info("No new businesses found this month")
        
        # Success response
        result = {
            'status': 'success',
            'message': 'NSW premises list workflow completed successfully',
            'current_month': {
                'month': current_month.strftime('%B %Y'),
                'filename': current_filename,
                'status': current_status,
                's3_location': current_s3_location
            },
            'previous_month': {
                'month': previous_month.strftime('%B %Y'),
                'filename': previous_filename,
                'status': previous_status,
                's3_location': previous_s3_location
            },
            'new_businesses': {
                'count': len(new_businesses),
                's3_location': f's3://{s3_bucket}/{new_businesses_s3_key}' if new_businesses_s3_key else None,
                'airtable_uploaded': airtable_upload_count
            }
        }
        
        logger.info("=" * 50)
        logger.info("WORKFLOW COMPLETED SUCCESSFULLY!")
        logger.info("=" * 50)
        logger.info(f"Current month file ({current_status}): {current_s3_location}")
        logger.info(f"Previous month file ({previous_status}): {previous_s3_location}")
        logger.info(f"New businesses found: {len(new_businesses)}")
        if new_businesses_s3_key:
            logger.info(f"New businesses saved to: s3://{s3_bucket}/{new_businesses_s3_key}")
        if airtable_upload_count is not None:
            logger.info(f"Airtable upload: {airtable_upload_count} businesses uploaded")
        
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