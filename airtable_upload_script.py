#!/usr/bin/env python3
"""
Airtable Upload Script for Business Contact Data

This script processes CSV files in the data/upload/ folder, splits email addresses
from 'Email Address' and 'Additional Email' columns into separate email_1 through 
email_5 columns, and uploads the data to Airtable.

Requirements:
- .env file with AIRTABLE_API_TOKEN, AIRTABLE_BASE_ID, and AIRTABLE_TABLE_NAME
- pyairtable library: pip install pyairtable
- python-dotenv library: pip install python-dotenv
"""

import csv
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from pyairtable import Api

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('airtable_upload.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AirtableUploader:
    def __init__(self):
        """Initialize the Airtable uploader with environment variables."""
        self.api_token = os.getenv('AIRTABLE_API_TOKEN')
        self.base_id = os.getenv('AIRTABLE_BASE_ID')
        self.table_name = os.getenv('AIRTABLE_TABLE_NAME')
        self.test_mode = os.getenv('TEST_MODE', 'False').lower() == 'true'
        
        if not all([self.api_token, self.base_id, self.table_name]):
            raise ValueError(
                "Missing required environment variables. Please check your .env file for:\n"
                "- AIRTABLE_API_TOKEN\n"
                "- AIRTABLE_BASE_ID\n"
                "- AIRTABLE_TABLE_NAME"
            )
        
        if not self.test_mode:
            self.api = Api(self.api_token)
            self.table = self.api.table(self.base_id, self.table_name)
        
        logger.info(f"Initialized AirtableUploader - Test Mode: {self.test_mode}")

    def process_emails(self, email_address: str, additional_email: str) -> Dict[str, str]:
        """
        Process emails from the Email Address and Additional Email columns.
        
        Args:
            email_address: Content from 'Email Address' column
            additional_email: Content from 'Additional Email' column
            
        Returns:
            Dictionary with 'Email Address' and 'Email Address 2' keys
        """
        # Return the emails as they are, mapping to the correct field names
        email_data = {
            'Email Address': email_address if email_address and email_address.strip() else '',
            'Email Address 2': additional_email if additional_email and additional_email.strip() else ''
        }
        
        return email_data

    def _convert_to_integer(self, value: str) -> Optional[int]:
        """
        Convert a string value to integer, handling decimals and invalid values.
        
        Args:
            value: String value to convert
            
        Returns:
            Integer value or None if conversion fails
        """
        if not value or value.strip() == '':
            return None
        
        try:
            # First try to convert to float (handles decimals like "2324.0")
            # then to int to remove decimal part
            float_val = float(str(value).strip())
            return int(float_val)
        except (ValueError, TypeError):
            # If conversion fails, return None
            return None

    def process_csv_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Process a single CSV file and return processed records.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            List of processed records ready for Airtable upload
        """
        processed_records = []
        
        logger.info(f"Processing file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8', newline='') as csvfile:
                # Try to detect the delimiter
                sample = csvfile.read(1024)
                csvfile.seek(0)
                
                # Use csv.Sniffer to detect delimiter
                try:
                    dialect = csv.Sniffer().sniff(sample)
                    reader = csv.DictReader(csvfile, dialect=dialect)
                except csv.Error:
                    # Fallback to comma delimiter
                    reader = csv.DictReader(csvfile)
                
                for row_num, row in enumerate(reader, start=2):  # Start at 2 because header is row 1
                    try:
                        # Process emails
                        email_address = row.get('Email Address', '')
                        additional_email = row.get('Additional Email', '')
                        email_data = self.process_emails(email_address, additional_email)
                        
                        # Create the processed record with proper data type handling
                        processed_record = {
                            'Name': row.get('Name', ''),
                            'Address': row.get('Address', ''),
                            'Suburb': row.get('Suburb', ''),
                            'Postcode': self._convert_to_integer(row.get('Postcode', '')),
                            'LGA': row.get('LGA', ''),
                            'Licensee': row.get('Licensee', ''),
                            'Licensee ABN': self._convert_to_integer(row.get('Licensee ABN', '')),
                            'Facebook Link': row.get('Facebook Link', ''),
                            'Instagram link': row.get('Instagram link', ''),
                            'Phone Number': row.get('Phone Number', ''),
                            'Notes': f'Source: {file_path.name}',
                            **email_data  # Add Email Address and Email Address 2
                        }
                        
                        # Only add records that have at least a name or email
                        if processed_record['Name'] or any(email_data.values()):
                            processed_records.append(processed_record)
                        
                    except Exception as e:
                        logger.error(f"Error processing row {row_num} in {file_path}: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return []
        
        logger.info(f"Processed {len(processed_records)} records from {file_path}")
        return processed_records

    def upload_to_airtable(self, records: List[Dict[str, Any]], batch_size: int = 10) -> bool:
        """
        Upload processed records to Airtable.
        
        Args:
            records: List of processed records
            batch_size: Number of records to upload in each batch
            
        Returns:
            True if successful, False otherwise
        """
        if self.test_mode:
            logger.info("TEST MODE: Would upload the following records:")
            for i, record in enumerate(records[:5]):  # Show first 5 records
                logger.info(f"Record {i+1}: {record}")
            if len(records) > 5:
                logger.info(f"... and {len(records) - 5} more records")
            return True
        
        try:
            total_uploaded = 0
            
            # Upload in batches
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                
                try:
                    # Clean the records - remove empty string values and None values
                    cleaned_batch = []
                    for record in batch:
                        cleaned_record = {}
                        for key, value in record.items():
                            if value is not None and value != '':
                                cleaned_record[key] = value
                        if cleaned_record:  # Only add non-empty records
                            cleaned_batch.append(cleaned_record)
                    
                    if cleaned_batch:
                        # Use the direct method call without 'fields' wrapper
                        result = self.table.batch_create(cleaned_batch)
                        total_uploaded += len(result)
                        logger.info(f"Uploaded batch {i//batch_size + 1}: {len(result)} records")
                    else:
                        logger.warning(f"Batch {i//batch_size + 1} was empty after cleaning")
                    
                    # Rate limiting - Airtable allows 5 requests per second
                    time.sleep(0.2)
                    
                except Exception as e:
                    logger.error(f"Error uploading batch {i//batch_size + 1}: {e}")
                    # Try alternative method for pyairtable compatibility
                    try:
                        # Alternative method - create records one by one if batch fails
                        for record in batch:
                            cleaned_record = {k: v for k, v in record.items() if v is not None and v != ''}
                            if cleaned_record:
                                result = self.table.create(cleaned_record)
                                total_uploaded += 1
                                time.sleep(0.1)  # Slower rate for individual uploads
                        logger.info(f"Uploaded batch {i//batch_size + 1} individually: {len(batch)} records")
                    except Exception as e2:
                        logger.error(f"Failed to upload batch {i//batch_size + 1} individually: {e2}")
                        continue
            
            logger.info(f"Successfully uploaded {total_uploaded} out of {len(records)} records")
            return total_uploaded > 0
            
        except Exception as e:
            logger.error(f"Error during upload process: {e}")
            return False

    def process_upload_folder(self, folder_path: str = "data/upload") -> None:
        """
        Process all CSV files in the upload folder and upload to Airtable.
        
        Args:
            folder_path: Path to the folder containing CSV files
        """
        upload_folder = Path(folder_path)
        
        if not upload_folder.exists():
            logger.error(f"Upload folder not found: {upload_folder}")
            return
        
        # Find all CSV files
        csv_files = list(upload_folder.glob("*.csv"))
        
        if not csv_files:
            logger.warning(f"No CSV files found in {upload_folder}")
            return
        
        logger.info(f"Found {len(csv_files)} CSV files to process")
        
        all_records = []
        
        # Process each CSV file
        for csv_file in csv_files:
            records = self.process_csv_file(csv_file)
            all_records.extend(records)
        
        if not all_records:
            logger.warning("No records to upload")
            return
        
        logger.info(f"Total records to upload: {len(all_records)}")
        
        # Upload to Airtable
        success = self.upload_to_airtable(all_records)
        
        if success:
            logger.info("Upload process completed successfully")
        else:
            logger.error("Upload process failed")

def main():
    """Main function to run the upload process."""
    try:
        uploader = AirtableUploader()
        uploader.process_upload_folder()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\nError: {e}")
        print("\nPlease make sure you have:")
        print("1. Created a .env file with your Airtable credentials")
        print("2. Installed required packages: pip install pyairtable python-dotenv")
        print("3. Check the env_template.txt file for the required environment variables")

if __name__ == "__main__":
    main()
