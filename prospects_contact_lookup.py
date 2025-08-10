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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('prospects_lookup.log'),
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
    
    def update_prospect_row(self, row, business_data):
        """
        Update a prospect row with found business data
        """
        if not business_data:
            return row
        
        # Update contact fields
        if business_data.get('phone'):
            row['Phone Number'] = business_data['phone']
        
        if business_data.get('website'):
            row['Facebook Link'] = business_data['website']  # Using Facebook field for website
        
        if business_data.get('emails'):
            # Use the first email found
            row['Email Address'] = business_data['emails'][0]
            
            # Add note about additional emails if found
            if len(business_data['emails']) > 1:
                additional_emails = ', '.join(business_data['emails'][1:])
                current_notes = row.get('Notes', '')
                row['Notes'] = f"{current_notes} | Additional emails: {additional_emails}"
        
        # Update notes with lookup timestamp
        current_notes = row.get('Notes', '')
        lookup_note = f"Contact lookup: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        row['Notes'] = f"{current_notes} | {lookup_note}" if current_notes else lookup_note
        
        return row
    
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
            
            # Update the row in the original dataframe
            if business_data:
                updated_row = self.update_prospect_row(row, business_data)
                for column, value in updated_row.items():
                    df.at[original_idx, column] = value
            
            # Rate limiting to be respectful
            time.sleep(2)
            
            # Progress update
            if idx % 5 == 0:
                logger.info(f"Progress: {idx}/{len(processing_df)} completed")
        
        # Save updated CSV
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            output_file = f"data/Prospects_with_Contacts_{timestamp}.csv"
        
        df.to_csv(output_file, index=False)
        logger.info(f"Updated prospects saved to: {output_file}")
        
        # Print summary
        self.print_summary()
        
        return df
    
    def print_summary(self):
        """
        Print summary of the lookup process
        """
        logger.info("=" * 80)
        logger.info("CONTACT LOOKUP SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total API calls made: {self.api_calls_made}")
        logger.info(f"Successful lookups: {self.successful_lookups}")
        logger.info(f"Failed lookups: {self.failed_lookups}")
        logger.info(f"Total emails found: {self.emails_found}")
        logger.info(f"Success rate: {self.successful_lookups/(self.successful_lookups + self.failed_lookups)*100:.1f}%")
        
        logger.info(f"\nAPI Usage Breakdown:")
        logger.info(f"Search calls: {self.api_limits['search_calls']}")
        logger.info(f"Details calls: {self.api_limits['details_calls']}")
        logger.info(f"Daily limit remaining: {self.api_limits['daily_limit'] - self.api_calls_made}")
        
        if self.successful_lookups > 0:
            logger.info(f"Average emails per successful lookup: {self.emails_found/self.successful_lookups:.1f}")


def main():
    """
    Main function with configuration
    """
    # Configuration
    GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API")
    PROSPECTS_FILE = "data/New_Prospects_20250809.csv"
    MAX_LOOKUPS = 20  # Limit for testing/free tier
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
        
        updated_df = processor.process_prospects(
            PROSPECTS_FILE,
            start_index=START_INDEX
        )
        
        logger.info("\nContact lookup completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user")
        processor.print_summary()
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        processor.print_summary()


if __name__ == "__main__":
    main()
