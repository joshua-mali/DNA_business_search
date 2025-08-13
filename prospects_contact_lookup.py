#!/usr/bin/env python3
"""
Prospects Contact Lookup Integration

This script processes the New_Prospects CSV file and uses the business contact scraper
to find contact details for each business. It's designed to work within Google API
free tier limits and provides detailed tracking of API usage.

Features:
- Processes CSV of new prospects
- Google Places API integration for business details
- Website scraping for email addresses
- API usage tracking to stay within free tier
- Detailed logging and progress tracking
- Updates the original CSV with found contact information
"""

import csv
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from business_lookup import BusinessContactScraper

# Load environment variables
load_dotenv()

# Configure logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('prospects_lookup.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ProspectsContactLookup:
    """
    Main class for processing prospects and finding contact details
    """
    
    def __init__(self, google_api_key, max_lookups=20):
        self.scraper = BusinessContactScraper(google_api_key)
        self.max_lookups = max_lookups
        self.api_calls_made = 0
        self.successful_lookups = 0
        self.failed_lookups = 0
        self.emails_found = 0
        
        # Track successful and failed businesses
        self.successful_businesses = []
        self.failed_businesses = []
        
        # Google Places API free tier limits (per day)
        self.api_limits = {
            'daily_limit': 2500,  # Free tier daily limit
            'search_calls': 0,    # Text search calls
            'details_calls': 0,   # Place details calls
        }
        
    def load_prospects_csv(self, csv_file):
        """
        Load the prospects CSV file
        """
        logger.info(f"Loading prospects from {csv_file}")
        
        try:
            df = pd.read_csv(csv_file)
            logger.info(f"Loaded {len(df)} prospects from CSV")
            return df
        except Exception as e:
            logger.error(f"Error loading CSV file: {e}")
            return None
    
    def format_search_query(self, row):
        """
        Format a search query for Google Places API based on prospect data
        """
        name = row.get('Name', '').strip()
        address = row.get('Address', '').strip()
        suburb = row.get('Suburb', '').strip()
        postcode = row.get('Postcode', '')
        
        # Create search query with business name and location
        query = name
        location = f"{suburb}, NSW {postcode}"
        
        # Clean up address for better matching
        if address:
            # Remove shop/unit numbers for cleaner search
            address_clean = address.replace('SHOP ', '').replace('UNIT ', '')
            location = f"{address_clean}, {location}"
        
        return query, location
    
    def lookup_business_contacts(self, row):
        """
        Lookup contact details for a single business
        """
        name = row.get('Name', '')
        logger.info(f"Looking up contacts for: {name}")
        
        try:
            # Format search query
            query, location = self.format_search_query(row)
            
            # Search for the business
            logger.debug(f"Searching: '{query}' in '{location}'")
            businesses = self.scraper.search_businesses(query, location, max_results=1)
            self.api_calls_made += 1
            self.api_limits['search_calls'] += 1
            
            if not businesses:
                logger.warning(f"No results found for {name}")
                self.failed_lookups += 1
                return None
            
            business = businesses[0]
            
            # Get additional place details if needed
            if business.get('website'):
                logger.info(f"Found website: {business['website']}")
                
                # Extract emails from website
                emails = self.scraper.extract_emails_from_website(business['website'])
                business['emails'] = emails
                
                if emails:
                    logger.info(f"Found {len(emails)} email(s): {', '.join(emails)}")
                    self.emails_found += len(emails)
                else:
                    logger.info("No emails found on website")
            
            self.successful_lookups += 1
            return business
            
        except Exception as e:
            logger.error(f"Error looking up {name}: {e}")
            self.failed_lookups += 1
            return None
    
    def create_airtable_row(self, original_row, business_data=None):
        """
        Create a clean row for Airtable import (removing unnecessary columns)
        """
        # Base columns for Airtable
        airtable_row = {
            'Name': original_row.get('Name', ''),
            'Address': original_row.get('Address', ''),
            'Suburb': original_row.get('Suburb', ''),
            'Postcode': original_row.get('Postcode', ''),
            'LGA': original_row.get('LGA', ''),
            'Licensee': original_row.get('Licensee', ''),
            'Licensee ABN': original_row.get('Licensee ABN', ''),
            'Facebook Link': '',
            'Instagram link': '',
            'Email Address': '',
            'Additional Email': '',
            'Phone Number': ''
        }
        
        # Add found contact data if available
        if business_data:
            if business_data.get('phone'):
                airtable_row['Phone Number'] = business_data['phone']
            
            if business_data.get('website'):
                airtable_row['Facebook Link'] = business_data['website']  # Using Facebook field for website
            
            if business_data.get('emails'):
                airtable_row['Email Address'] = business_data['emails'][0]
                
                # If multiple emails found, add second one to Additional Email field
                if len(business_data['emails']) > 1:
                    airtable_row['Additional Email'] = business_data['emails'][1]
                    
                    # If more than 2 emails, add remaining to Instagram field
                    if len(business_data['emails']) > 2:
                        remaining_emails = ', '.join(business_data['emails'][2:])
                        airtable_row['Instagram link'] = f"More emails: {remaining_emails}"
        
        return airtable_row
    
    def has_contact_info(self, business_data):
        """
        Check if business data contains email addresses (our success criteria)
        """
        if not business_data:
            return False
        
        # Success criteria: Must have at least one email address
        return bool(business_data.get('emails'))
    
    def process_prospects(self, csv_file, output_file=None, start_index=0):
        """
        Process prospects CSV and lookup contact details
        """
        logger.info("=" * 80)
        logger.info("STARTING PROSPECTS CONTACT LOOKUP")
        logger.info("=" * 80)
        
        # Load prospects
        df = self.load_prospects_csv(csv_file)
        if df is None:
            return
        
        # Limit processing
        end_index = min(start_index + self.max_lookups, len(df))
        processing_df = df.iloc[start_index:end_index].copy()
        
        logger.info(f"Processing prospects {start_index + 1} to {end_index} of {len(df)} total")
        logger.info(f"API calls budget: {self.max_lookups} lookups")
        
        # Process each prospect
        for idx, (original_idx, row) in enumerate(processing_df.iterrows(), 1):
            logger.info(f"\n--- Processing {idx}/{len(processing_df)}: {row['Name']} ---")
            
            # Check API limits
            if self.api_calls_made >= self.max_lookups:
                logger.warning("API call limit reached, stopping processing")
                break
            
            # Lookup business contacts
            business_data = self.lookup_business_contacts(row)
            
            # Create clean Airtable row
            airtable_row = self.create_airtable_row(row, business_data)
            
            # Categorize based on whether email addresses were found
            if self.has_contact_info(business_data):
                self.successful_businesses.append(airtable_row)
                logger.info("SUCCESS: Email address found - added to successful list")
            else:
                self.failed_businesses.append(airtable_row)
                logger.info("RETRY: No email address found - added to retry list")
            
            # Rate limiting to be respectful
            time.sleep(2)
            
            # Progress update
            if idx % 5 == 0:
                logger.info(f"Progress: {idx}/{len(processing_df)} completed")
        
        # Save separate CSV files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # File 1: Businesses with contact info (ready for Airtable)
        if self.successful_businesses:
            successful_file = f"data/Contacts_Found_{timestamp}.csv"
            successful_df = pd.DataFrame(self.successful_businesses)
            successful_df.to_csv(successful_file, index=False)
            logger.info(f"Businesses with email addresses saved to: {successful_file}")
        
        # File 2: Businesses without contact info (for retry/AI processing)
        if self.failed_businesses:
            failed_file = f"data/No_Contacts_Found_{timestamp}.csv"
            failed_df = pd.DataFrame(self.failed_businesses)
            failed_df.to_csv(failed_file, index=False)
            logger.info(f"Businesses needing retry saved to: {failed_file}")
        
        # Remove processed businesses from original CSV to avoid duplicates in future runs
        self.remove_processed_businesses(df, start_index, end_index, csv_file)
        
        # Print summary
        self.print_summary()
        
        return self.successful_businesses, self.failed_businesses
    
    def remove_processed_businesses(self, df, start_index, end_index, original_csv_file):
        """
        Remove processed businesses from the original CSV file
        """
        try:
            # Create backup of original file
            backup_file = f"{original_csv_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M')}"
            df_backup = df.copy()
            df_backup.to_csv(backup_file, index=False)
            logger.info(f"Backup created: {backup_file}")
            
            # Remove the processed rows
            remaining_df = df.drop(df.index[start_index:end_index])
            
            # Save updated original file
            remaining_df.to_csv(original_csv_file, index=False)
            
            processed_count = end_index - start_index
            remaining_count = len(remaining_df)
            
            logger.info(f"Removed {processed_count} processed businesses from original CSV")
            logger.info(f"Remaining businesses in queue: {remaining_count}")
            
            if remaining_count > 0:
                logger.info(f"Next run will start with: {remaining_df.iloc[0]['Name']} in {remaining_df.iloc[0]['Suburb']}")
            else:
                logger.info("All businesses have been processed!")
            
        except Exception as e:
            logger.error(f"Error removing processed businesses: {e}")
            logger.info("Original CSV file remains unchanged")
    
    def print_summary(self):
        """
        Print summary of the lookup process
        """
        logger.info("=" * 80)
        logger.info("CONTACT LOOKUP SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total API calls made: {self.api_calls_made}")
        logger.info(f"Businesses with EMAIL addresses found: {len(self.successful_businesses)}")
        logger.info(f"Businesses needing retry (no emails): {len(self.failed_businesses)}")
        logger.info(f"Total emails found: {self.emails_found}")
        
        total_processed = len(self.successful_businesses) + len(self.failed_businesses)
        if total_processed > 0:
            success_rate = len(self.successful_businesses) / total_processed * 100
            logger.info(f"Email success rate: {success_rate:.1f}%")
        
        logger.info(f"\nAPI Usage Breakdown:")
        logger.info(f"Search calls: {self.api_limits['search_calls']}")
        logger.info(f"Details calls: {self.api_limits['details_calls']}")
        logger.info(f"Daily limit remaining: {self.api_limits['daily_limit'] - self.api_calls_made}")
        
        if len(self.successful_businesses) > 0:
            avg_emails = self.emails_found / len(self.successful_businesses)
            logger.info(f"Average emails per successful business: {avg_emails:.1f}")
        
        logger.info(f"\nFiles Generated:")
        if self.successful_businesses:
            logger.info(f"SUCCESS: Contacts_Found_*.csv - {len(self.successful_businesses)} businesses ready for Airtable")
        if self.failed_businesses:
            logger.info(f"RETRY: No_Contacts_Found_*.csv - {len(self.failed_businesses)} businesses for AI/manual retry")


def main():
    """
    Main function with configuration
    """
    # Configuration
    GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API")
    PROSPECTS_FILE = "data/New_Prospects_20250809.csv"
    MAX_LOOKUPS = 500  # Limit for testing/free tier
    START_INDEX = 0   # Which prospect to start from (0 = first)
    
    # Validate API key
    if not GOOGLE_API_KEY:
        logger.error("Google API key not found in environment variables")
        logger.error("Please set GOOGLE_PLACES_API in your .env file")
        return
    
    # Validate input file
    if not Path(PROSPECTS_FILE).exists():
        logger.error(f"Prospects file not found: {PROSPECTS_FILE}")
        return
    
    # Initialize lookup processor
    processor = ProspectsContactLookup(GOOGLE_API_KEY, max_lookups=MAX_LOOKUPS)
    
    # Process prospects
    try:
        logger.info(f"Starting contact lookup for {MAX_LOOKUPS} prospects...")
        logger.info(f"Using API key: ...{GOOGLE_API_KEY[-8:] if GOOGLE_API_KEY else 'None'}")
        
        successful_businesses, failed_businesses = processor.process_prospects(
            PROSPECTS_FILE,
            start_index=START_INDEX
        )
        
        logger.info("\nContact lookup completed successfully!")
        logger.info(f"Results: {len(successful_businesses)} with emails, {len(failed_businesses)} need retry")
        
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user")
        processor.print_summary()
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        processor.print_summary()


if __name__ == "__main__":
    main()
