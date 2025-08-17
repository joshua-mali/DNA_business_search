#!/usr/bin/env python3
"""
AWS Lambda Monthly NSW Distillery Business Search Workflow

This Lambda function automates the complete monthly process:
1. Downloads current and previous month's NSW premises lists
2. Identifies new businesses
3. Filters for target business types
4. Runs contact lookup using Google Places API
5. Saves results to S3
6. Sends summary report via SNS/email

Designed to run monthly via CloudWatch Events/EventBridge.
"""

import json
import logging
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import boto3
import pandas as pd
import requests

# Import our existing business logic
from generate_new_prospects import (BusinessMatcher,
                                    convert_licensee_to_contact_format,
                                    filter_target_businesses)
from prospects_contact_lookup import ProspectsContactLookup

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
s3_client = boto3.client('s3')
sns_client = boto3.client('sns')


class LambdaMonthlyWorkflow:
    """
    AWS Lambda handler for monthly business search workflow
    """
    
    def __init__(self):
        # Environment variables
        self.s3_bucket = os.environ.get('S3_BUCKET', 'nsw-distillery-search')
        self.sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')
        self.google_api_key = os.environ.get('GOOGLE_PLACES_API')
        self.max_contact_lookups = int(os.environ.get('MAX_CONTACT_LOOKUPS', '100'))
        
        # NSW Government data URLs (these may need updating)
        self.nsw_base_url = "https://www.liquorandgaming.nsw.gov.au"
        self.premises_list_url_pattern = self.nsw_base_url + "/documents/liquor-licence/premises-list-{month}-{year}.csv"
        
        # S3 paths
        self.s3_data_prefix = "data/"
        self.s3_output_prefix = "monthly_output/"
        self.s3_contact_db_key = "data/contact_database.csv"
        
        # Working directory in Lambda
        self.temp_dir = Path(tempfile.gettempdir())
        
        # Initialize contact lookup
        if self.google_api_key:
            self.contact_lookup = ProspectsContactLookup(
                self.google_api_key, 
                max_lookups=self.max_contact_lookups
            )
        else:
            self.contact_lookup = None
            logger.warning("Google API key not provided - contact lookup disabled")
    
    def get_current_and_previous_months(self):
        """
        Calculate current and previous month for data download
        """
        now = datetime.now()
        
        # Current month (or previous if we're early in the month)
        if now.day < 5:  # Run on 5th of month to ensure previous month data is available
            current_month = now.replace(day=1) - timedelta(days=1)  # Last month
        else:
            current_month = now.replace(day=1)  # This month
        
        # Previous month
        previous_month = (current_month.replace(day=1) - timedelta(days=1))
        
        return current_month, previous_month
    
    def download_nsw_premises_list(self, year, month, filename):
        """
        Download NSW premises list for a specific month/year
        """
        # Try different month name formats NSW might use
        month_formats = [
            month.strftime("%b"),      # "Jul"
            month.strftime("%B"),      # "July"  
            month.strftime("%m"),      # "07"
            f"{month.strftime('%b')}-{year}"  # "Jul-2025"
        ]
        
        for month_format in month_formats:
            url = self.premises_list_url_pattern.format(
                month=month_format, 
                year=year
            )
            
            try:
                logger.info(f"Attempting download from: {url}")
                response = requests.get(url, timeout=30)
                
                if response.status_code == 200:
                    # Save to temp file
                    file_path = self.temp_dir / filename
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    
                    logger.info(f"Successfully downloaded: {filename}")
                    return str(file_path)
                    
            except Exception as e:
                logger.warning(f"Failed to download from {url}: {e}")
                continue
        
        raise Exception(f"Could not download premises list for {month.strftime('%B %Y')}")
    
    def upload_to_s3(self, local_file_path, s3_key):
        """
        Upload file to S3
        """
        try:
            s3_client.upload_file(local_file_path, self.s3_bucket, s3_key)
            logger.info(f"Uploaded {local_file_path} to s3://{self.s3_bucket}/{s3_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}")
            return False
    
    def download_from_s3(self, s3_key, local_file_path):
        """
        Download file from S3
        """
        try:
            s3_client.download_file(self.s3_bucket, s3_key, local_file_path)
            logger.info(f"Downloaded s3://{self.s3_bucket}/{s3_key} to {local_file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download from S3: {e}")
            return False
    
    def load_existing_contact_database(self):
        """
        Load existing contact database from S3
        """
        contact_db_path = self.temp_dir / "contact_database.csv"
        
        if self.download_from_s3(self.s3_contact_db_key, str(contact_db_path)):
            return pd.read_csv(contact_db_path)
        else:
            logger.warning("No existing contact database found, starting fresh")
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=[
                'Name', 'Address', 'Suburb', 'Postcode', 'LGA', 
                'Licensee', 'Licensee ABN', 'Facebook Link', 'Instagram link', 
                'Email Address', 'Additional Email', 'Phone Number'
            ])
    
    def identify_new_licenses(self, current_df, previous_df):
        """
        Identify genuinely new licenses (same logic as monthly_workflow.py)
        """
        logger.info("Identifying new licenses...")
        
        # Get license numbers from previous month
        previous_license_numbers = set(previous_df['Licence number'].dropna())
        
        # Find completely new licenses
        new_licenses_df = current_df[
            ~current_df['Licence number'].isin(previous_license_numbers)
        ].copy()
        
        # Find licenses that became active/trading
        previous_non_trading = previous_df[
            (previous_df['Trading Status'] != 'Trading') |
            (previous_df['Status'] != 'Current')
        ]['Licence number'].dropna()
        
        current_trading = current_df[
            (current_df['Trading Status'] == 'Trading') &
            (current_df['Status'] == 'Current')
        ]
        
        newly_trading_df = current_trading[
            current_trading['Licence number'].isin(previous_non_trading)
        ].copy()
        
        # Combine and deduplicate
        all_new_df = pd.concat([new_licenses_df, newly_trading_df], ignore_index=True)
        all_new_df = all_new_df.drop_duplicates(subset=['Licence number'])
        
        logger.info(f"Found {len(new_licenses_df)} new licenses and {len(newly_trading_df)} newly trading")
        logger.info(f"Total new opportunities: {len(all_new_df)}")
        
        return all_new_df
    
    def run_contact_lookup_on_prospects(self, prospects_df):
        """
        Run contact lookup on new prospects using Google Places API
        """
        if not self.contact_lookup:
            logger.warning("Contact lookup disabled - no Google API key")
            return prospects_df, pd.DataFrame()
        
        logger.info(f"Running contact lookup on {len(prospects_df)} prospects...")
        
        # Save prospects to temp CSV for contact lookup
        prospects_file = self.temp_dir / "new_prospects.csv"
        prospects_df.to_csv(prospects_file, index=False)
        
        # Run contact lookup
        successful_businesses, failed_businesses = self.contact_lookup.process_prospects(
            str(prospects_file),
            start_index=0
        )
        
        # Convert results back to DataFrames
        contacts_found_df = pd.DataFrame(successful_businesses) if successful_businesses else pd.DataFrame()
        no_contacts_df = pd.DataFrame(failed_businesses) if failed_businesses else pd.DataFrame()
        
        logger.info(f"Contact lookup results: {len(contacts_found_df)} with emails, {len(no_contacts_df)} without")
        
        return contacts_found_df, no_contacts_df
    
    def update_contact_database(self, existing_contacts_df, new_contacts_df):
        """
        Update the contact database with new contacts
        """
        if len(new_contacts_df) == 0:
            return existing_contacts_df
        
        # Combine and remove duplicates
        updated_df = pd.concat([existing_contacts_df, new_contacts_df], ignore_index=True)
        updated_df = updated_df.drop_duplicates(subset=['Name', 'Suburb'], keep='last')
        
        logger.info(f"Contact database updated: {len(existing_contacts_df)} -> {len(updated_df)} contacts")
        
        return updated_df
    
    def generate_monthly_report(self, workflow_stats):
        """
        Generate monthly summary report
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""
NSW DISTILLERY BUSINESS SEARCH - MONTHLY LAMBDA REPORT
Generated: {timestamp}
================================================================================

WORKFLOW SUMMARY:
- Execution: AWS Lambda automated run
- Current month data: {workflow_stats.get('current_month', 'N/A')}
- Previous month data: {workflow_stats.get('previous_month', 'N/A')}

DATA PROCESSING:
- Current month licensees: {workflow_stats.get('current_licensees', 0):,}
- Previous month licensees: {workflow_stats.get('previous_licensees', 0):,}
- New licenses identified: {workflow_stats.get('new_licenses', 0):,}
- Target business matches: {workflow_stats.get('target_businesses', 0):,}
- Prospects after deduplication: {workflow_stats.get('new_prospects', 0):,}

CONTACT LOOKUP RESULTS:
- Businesses with emails found: {workflow_stats.get('contacts_found', 0):,}
- Businesses needing retry: {workflow_stats.get('no_contacts', 0):,}
- Contact success rate: {workflow_stats.get('contact_success_rate', 0):.1f}%
- API calls made: {workflow_stats.get('api_calls', 0):,}

FILES GENERATED:
- Contacts ready for Airtable: {workflow_stats.get('contacts_file', 'N/A')}
- Businesses needing retry: {workflow_stats.get('retry_file', 'N/A')}
- Updated contact database: {workflow_stats.get('contact_db_file', 'N/A')}

COSTS:
- Estimated Google API cost: ${workflow_stats.get('estimated_cost', 0):.2f}
- Lambda execution cost: ~$0.01

NEXT STEPS:
1. Download contacts file from S3 and upload to Airtable
2. Review retry businesses for manual/AI processing
3. Monitor for next month's automated run

================================================================================
"""
        
        return report
    
    def send_notification(self, report):
        """
        Send notification via SNS
        """
        if not self.sns_topic_arn:
            logger.warning("No SNS topic configured - skipping notification")
            return
        
        try:
            sns_client.publish(
                TopicArn=self.sns_topic_arn,
                Subject="NSW Distillery Monthly Search - Completed",
                Message=report
            )
            logger.info("Notification sent via SNS")
        except Exception as e:
            logger.error(f"Failed to send SNS notification: {e}")


def lambda_handler(event, context):
    """
    Main Lambda handler function
    """
    workflow = LambdaMonthlyWorkflow()
    workflow_stats = {}
    
    try:
        logger.info("Starting monthly NSW distillery business search workflow")
        
        # Step 1: Determine current and previous months
        current_month, previous_month = workflow.get_current_and_previous_months()
        workflow_stats['current_month'] = current_month.strftime("%B %Y")
        workflow_stats['previous_month'] = previous_month.strftime("%B %Y")
        
        logger.info(f"Processing: {workflow_stats['current_month']} vs {workflow_stats['previous_month']}")
        
        # Step 2: Download NSW premises lists
        current_file = workflow.download_nsw_premises_list(
            current_month.year, 
            current_month, 
            f"premises-list-{current_month.strftime('%b-%Y')}.csv"
        )
        
        previous_file = workflow.download_nsw_premises_list(
            previous_month.year, 
            previous_month, 
            f"premises-list-{previous_month.strftime('%b-%Y')}.csv"
        )
        
        # Upload to S3 for record keeping
        workflow.upload_to_s3(current_file, f"{workflow.s3_data_prefix}current-month.csv")
        workflow.upload_to_s3(previous_file, f"{workflow.s3_data_prefix}previous-month.csv")
        
        # Step 3: Load and process data
        current_df = pd.read_csv(current_file, skiprows=3)
        previous_df = pd.read_csv(previous_file, skiprows=3)
        
        workflow_stats['current_licensees'] = len(current_df)
        workflow_stats['previous_licensees'] = len(previous_df)
        
        # Step 4: Identify new licenses
        new_licenses_df = workflow.identify_new_licenses(current_df, previous_df)
        workflow_stats['new_licenses'] = len(new_licenses_df)
        
        # Step 5: Filter for target businesses
        target_businesses_df = filter_target_businesses(new_licenses_df)
        workflow_stats['target_businesses'] = len(target_businesses_df)
        
        # Step 6: Load existing contact database and deduplicate
        existing_contacts_df = workflow.load_existing_contact_database()
        
        matcher = BusinessMatcher(similarity_threshold=85)
        new_prospects = []
        
        for _, licensee_row in target_businesses_df.iterrows():
            is_duplicate, match_reason = matcher.find_matches(existing_contacts_df, licensee_row)
            
            if not is_duplicate:
                new_prospect = convert_licensee_to_contact_format(licensee_row)
                new_prospects.append(new_prospect)
        
        prospects_df = pd.DataFrame(new_prospects)
        workflow_stats['new_prospects'] = len(prospects_df)
        
        # Step 7: Run contact lookup if we have prospects
        contacts_found_df = pd.DataFrame()
        no_contacts_df = pd.DataFrame()
        
        if len(prospects_df) > 0 and workflow.contact_lookup:
            contacts_found_df, no_contacts_df = workflow.run_contact_lookup_on_prospects(prospects_df)
            
            workflow_stats['contacts_found'] = len(contacts_found_df)
            workflow_stats['no_contacts'] = len(no_contacts_df)
            workflow_stats['api_calls'] = workflow.contact_lookup.api_calls_made
            workflow_stats['estimated_cost'] = workflow.contact_lookup.api_calls_made * 0.032
            
            if len(contacts_found_df) + len(no_contacts_df) > 0:
                success_rate = len(contacts_found_df) / (len(contacts_found_df) + len(no_contacts_df)) * 100
                workflow_stats['contact_success_rate'] = success_rate
        
        # Step 8: Save results to S3
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        if len(contacts_found_df) > 0:
            contacts_file = workflow.temp_dir / f"contacts_found_{timestamp}.csv"
            contacts_found_df.to_csv(contacts_file, index=False)
            workflow.upload_to_s3(str(contacts_file), f"{workflow.s3_output_prefix}contacts_found_{timestamp}.csv")
            workflow_stats['contacts_file'] = f"contacts_found_{timestamp}.csv"
        
        if len(no_contacts_df) > 0:
            retry_file = workflow.temp_dir / f"no_contacts_{timestamp}.csv"
            no_contacts_df.to_csv(retry_file, index=False)
            workflow.upload_to_s3(str(retry_file), f"{workflow.s3_output_prefix}no_contacts_{timestamp}.csv")
            workflow_stats['retry_file'] = f"no_contacts_{timestamp}.csv"
        
        # Step 9: Update contact database
        if len(contacts_found_df) > 0:
            updated_contacts_df = workflow.update_contact_database(existing_contacts_df, contacts_found_df)
            contact_db_file = workflow.temp_dir / "updated_contact_database.csv"
            updated_contacts_df.to_csv(contact_db_file, index=False)
            workflow.upload_to_s3(str(contact_db_file), workflow.s3_contact_db_key)
            workflow_stats['contact_db_file'] = "contact_database.csv"
        
        # Step 10: Generate and send report
        report = workflow.generate_monthly_report(workflow_stats)
        workflow.send_notification(report)
        
        logger.info("Monthly workflow completed successfully")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Monthly workflow completed successfully',
                'stats': workflow_stats
            })
        }
        
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        
        # Send failure notification
        if workflow.sns_topic_arn:
            try:
                sns_client.publish(
                    TopicArn=workflow.sns_topic_arn,
                    Subject="NSW Distillery Monthly Search - FAILED",
                    Message=f"Monthly workflow failed with error: {str(e)}"
                )
            except:
                pass
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'stats': workflow_stats
            })
        }


# For local testing
if __name__ == "__main__":
    # Set environment variables for testing
    os.environ['S3_BUCKET'] = 'nsw-distillery-search-test'
    os.environ['MAX_CONTACT_LOOKUPS'] = '5'  # Small number for testing
    
    # Mock Lambda context
    class MockContext:
        def __init__(self):
            self.function_name = 'test-function'
            self.memory_limit_in_mb = 512
            self.invoked_function_arn = 'arn:aws:lambda:test'
    
    # Run local test
    result = lambda_handler({}, MockContext())
    print(json.dumps(result, indent=2))
