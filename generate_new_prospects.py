#!/usr/bin/env python3
"""
New Prospects Generator for NSW Distillery Business Search

This script identifies new businesses from the NSW Government licensee data
that are not already present in the existing contact database.

It uses multiple matching strategies to avoid duplicates:
1. ABN matching (most reliable)
2. Business name + suburb matching
3. Licensee name + suburb matching
4. Address similarity matching

The output is a CSV file in the same format as the existing contact database,
containing only new prospects that need contact research.
"""

import logging
import re
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import pandas as pd
from fuzzywuzzy import fuzz, process

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BusinessMatcher:
    """
    Class to handle matching businesses between contact database and licensee data
    """
    
    def __init__(self, similarity_threshold=85):
        self.similarity_threshold = similarity_threshold
        self.abn_matches = 0
        self.name_suburb_matches = 0
        self.licensee_suburb_matches = 0
        self.address_matches = 0
        
    def clean_abn(self, abn):
        """Clean and standardize ABN format"""
        if pd.isna(abn):
            return None
        abn_str = str(abn).strip()
        # Remove any non-digit characters
        abn_clean = re.sub(r'\D', '', abn_str)
        # ABN should be 11 digits
        if len(abn_clean) == 11:
            return abn_clean
        return None
    
    def clean_business_name(self, name):
        """Clean and standardize business name for comparison"""
        if pd.isna(name):
            return ""
        
        name = str(name).upper().strip()
        
        # Remove common business suffixes/prefixes
        patterns_to_remove = [
            r'\bPTY\s*LTD\b',
            r'\bLIMITED\b',
            r'\bLTD\b',
            r'\bPTY\b',
            r'\bCO\b',
            r'\bINC\b',
            r'\bCORP\b',
            r'\b&\b',
            r'\bTHE\b',
        ]
        
        for pattern in patterns_to_remove:
            name = re.sub(pattern, ' ', name)
        
        # Remove extra whitespace and special characters
        name = re.sub(r'[^\w\s]', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    
    def clean_address(self, address):
        """Clean and standardize address for comparison"""
        if pd.isna(address):
            return ""
        
        address = str(address).upper().strip()
        
        # Standardize common address terms
        replacements = {
            r'\bSTREET\b': 'ST',
            r'\bROAD\b': 'RD',
            r'\bAVENUE\b': 'AV',
            r'\bDRIVE\b': 'DR',
            r'\bCLOSE\b': 'CL',
            r'\bCOURT\b': 'CT',
            r'\bPLACE\b': 'PL',
            r'\bCRESCENT\b': 'CRES',
            r'\bPARADE\b': 'PDE',
            r'\bTERRACE\b': 'TCE',
            r'\bUNIT\s*\d+\s*': '',
            r'\bSHOP\s*\d+\s*': '',
        }
        
        for pattern, replacement in replacements.items():
            address = re.sub(pattern, replacement, address)
        
        # Remove extra whitespace and special characters except numbers
        address = re.sub(r'[^\w\s]', ' ', address)
        address = re.sub(r'\s+', ' ', address).strip()
        
        return address
    
    def clean_suburb(self, suburb):
        """Clean and standardize suburb name"""
        if pd.isna(suburb):
            return ""
        return str(suburb).upper().strip()
    
    def is_match_by_abn(self, contact_abn, licensee_abn):
        """Check if ABNs match"""
        contact_clean = self.clean_abn(contact_abn)
        licensee_clean = self.clean_abn(licensee_abn)
        
        if contact_clean and licensee_clean:
            return contact_clean == licensee_clean
        return False
    
    def is_match_by_name_suburb(self, contact_name, contact_suburb, licensee_name, licensee_suburb):
        """Check if business name and suburb match"""
        contact_name_clean = self.clean_business_name(contact_name)
        licensee_name_clean = self.clean_business_name(licensee_name)
        contact_suburb_clean = self.clean_suburb(contact_suburb)
        licensee_suburb_clean = self.clean_suburb(licensee_suburb)
        
        if not contact_name_clean or not licensee_name_clean:
            return False
        
        # Check suburb match first (must be exact)
        if contact_suburb_clean != licensee_suburb_clean:
            return False
        
        # Check name similarity
        similarity = fuzz.ratio(contact_name_clean, licensee_name_clean)
        return similarity >= self.similarity_threshold
    
    def is_match_by_licensee_suburb(self, contact_licensee, contact_suburb, licensee_licensee, licensee_suburb):
        """Check if licensee name and suburb match"""
        contact_licensee_clean = self.clean_business_name(contact_licensee)
        licensee_licensee_clean = self.clean_business_name(licensee_licensee)
        contact_suburb_clean = self.clean_suburb(contact_suburb)
        licensee_suburb_clean = self.clean_suburb(licensee_suburb)
        
        if not contact_licensee_clean or not licensee_licensee_clean:
            return False
        
        # Check suburb match first (must be exact)
        if contact_suburb_clean != licensee_suburb_clean:
            return False
        
        # Check licensee name similarity
        similarity = fuzz.ratio(contact_licensee_clean, licensee_licensee_clean)
        return similarity >= self.similarity_threshold
    
    def is_match_by_address(self, contact_address, contact_suburb, licensee_address, licensee_suburb):
        """Check if addresses match"""
        contact_address_clean = self.clean_address(contact_address)
        licensee_address_clean = self.clean_address(licensee_address)
        contact_suburb_clean = self.clean_suburb(contact_suburb)
        licensee_suburb_clean = self.clean_suburb(licensee_suburb)
        
        if not contact_address_clean or not licensee_address_clean:
            return False
        
        # Check suburb match first
        if contact_suburb_clean != licensee_suburb_clean:
            return False
        
        # Check address similarity
        similarity = fuzz.ratio(contact_address_clean, licensee_address_clean)
        return similarity >= 90  # Higher threshold for addresses
    
    def find_matches(self, contact_df, licensee_row):
        """
        Find if a licensee row matches any business in the contact database
        Returns True if match found, False otherwise
        """
        licensee_abn = licensee_row.get('Licensee ABN')
        licensee_name = licensee_row.get('Licence name')
        licensee_licensee = licensee_row.get('Licensee')
        licensee_address = licensee_row.get('Address')
        licensee_suburb = licensee_row.get('Suburb')
        
        for _, contact_row in contact_df.iterrows():
            # Strategy 1: ABN matching (most reliable)
            if self.is_match_by_abn(contact_row.get('Licensee ABN'), licensee_abn):
                self.abn_matches += 1
                return True, "ABN match"
            
            # Strategy 2: Business name + suburb matching
            if self.is_match_by_name_suburb(
                contact_row.get('Name'), contact_row.get('Suburb'),
                licensee_name, licensee_suburb
            ):
                self.name_suburb_matches += 1
                return True, "Name + Suburb match"
            
            # Strategy 3: Licensee + suburb matching
            if self.is_match_by_licensee_suburb(
                contact_row.get('Licensee'), contact_row.get('Suburb'),
                licensee_licensee, licensee_suburb
            ):
                self.licensee_suburb_matches += 1
                return True, "Licensee + Suburb match"
            
            # Strategy 4: Address matching
            if self.is_match_by_address(
                contact_row.get('Address'), contact_row.get('Suburb'),
                licensee_address, licensee_suburb
            ):
                self.address_matches += 1
                return True, "Address match"
        
        return False, "No match"


def filter_target_businesses(licensee_df):
    """
    Filter licensee data to only include target business types
    """
    logger.info("Filtering licensee data for target business types...")
    
    # Target business types for distillery customers
    target_business_types = [
        'Restaurant',
        'Full hotel',
        'Multi-function',
        'General bar',
        'Accommodation,Restaurant',
        'Catering service',
        'Sport facility',
        'Theatre public entertainment venue',
        'Club activity and support',
        'Accommodation,Catering service,Restaurant'
    ]
    
    # Target license types
    target_license_types = [
        'Liquor - on-premises licence',
        'Liquor - hotel licence',
        'Liquor - club licence',
        'Liquor - small bar licence',
        'Liquor - limited licence'
    ]
    
    # Filter criteria
    filtered_df = licensee_df[
        (licensee_df['Status'] == 'Current') &
        (licensee_df['Trading Status'] == 'Trading') &
        (licensee_df['Licence type'].isin(target_license_types)) &
        (licensee_df['Business type'].isin(target_business_types))
    ].copy()
    
    logger.info(f"Filtered from {len(licensee_df):,} to {len(filtered_df):,} target businesses")
    
    return filtered_df


def convert_licensee_to_contact_format(licensee_row):
    """
    Convert a licensee row to the contact database format
    """
    return {
        'Name': licensee_row.get('Licence name', ''),
        'Address': licensee_row.get('Address', ''),
        'Suburb': licensee_row.get('Suburb', ''),
        'Postcode': licensee_row.get('Postcode', ''),
        'LGA': licensee_row.get('LGA', ''),
        'Licensee': licensee_row.get('Licensee', ''),
        'Licensee ABN': licensee_row.get('Licensee ABN', ''),
        'Facebook Link': '',  # To be filled by future automation
        'Instagram link': '',  # To be filled by future automation
        'Email Address': '',  # To be filled by future automation
        'Phone Number': '',  # To be filled by future automation
        'Date email 1 sent': '',
        'Date email 2 sent': '',
        'Date email 3 sent': '',
        'Notes': f"New prospect from {licensee_row.get('Start date', '')} licensee data",
        '': ''  # Empty column to match original format
    }


def generate_new_prospects(contact_file, licensee_file, output_file):
    """
    Main function to generate new prospects CSV
    """
    logger.info("Starting new prospects generation...")
    
    # Load contact database
    logger.info("Loading existing contact database...")
    contact_df = pd.read_csv(contact_file)
    logger.info(f"Loaded {len(contact_df):,} existing contacts")
    
    # Load licensee data
    logger.info("Loading NSW licensee data...")
    licensee_df = pd.read_csv(licensee_file, skiprows=3)
    logger.info(f"Loaded {len(licensee_df):,} licensee records")
    
    # Filter to target business types
    filtered_licensee_df = filter_target_businesses(licensee_df)
    
    # Initialize matcher
    matcher = BusinessMatcher(similarity_threshold=85)
    
    # Find new prospects
    logger.info("Finding new prospects (this may take a few minutes)...")
    new_prospects = []
    total_processed = 0
    
    for idx, licensee_row in filtered_licensee_df.iterrows():
        total_processed += 1
        
        if total_processed % 500 == 0:
            logger.info(f"Processed {total_processed:,} of {len(filtered_licensee_df):,} businesses...")
        
        is_duplicate, match_reason = matcher.find_matches(contact_df, licensee_row)
        
        if not is_duplicate:
            # Convert to contact format and add to new prospects
            new_prospect = convert_licensee_to_contact_format(licensee_row)
            new_prospects.append(new_prospect)
    
    # Create output DataFrame
    new_prospects_df = pd.DataFrame(new_prospects)
    
    # Save to CSV
    new_prospects_df.to_csv(output_file, index=False)
    
    # Print summary
    logger.info("=" * 80)
    logger.info("NEW PROSPECTS GENERATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Total licensee records: {len(licensee_df):,}")
    logger.info(f"Filtered target businesses: {len(filtered_licensee_df):,}")
    logger.info(f"Existing contacts: {len(contact_df):,}")
    logger.info(f"New prospects found: {len(new_prospects):,}")
    logger.info(f"Output saved to: {output_file}")
    
    logger.info("\nDuplication Detection Summary:")
    logger.info(f"ABN matches: {matcher.abn_matches:,}")
    logger.info(f"Name + Suburb matches: {matcher.name_suburb_matches:,}")
    logger.info(f"Licensee + Suburb matches: {matcher.licensee_suburb_matches:,}")
    logger.info(f"Address matches: {matcher.address_matches:,}")
    logger.info(f"Total duplicates removed: {matcher.abn_matches + matcher.name_suburb_matches + matcher.licensee_suburb_matches + matcher.address_matches:,}")
    
    return new_prospects_df


def main():
    """
    Main function
    """
    # File paths
    contact_file = "data/Businesses up to Sep 2024.csv"
    licensee_file = "data/premises-list-Jul-2025 - premises list.csv"
    output_file = "data/New_Prospects_" + pd.Timestamp.now().strftime("%Y%m%d") + ".csv"
    
    # Check if files exist
    if not Path(contact_file).exists():
        logger.error(f"Contact file not found: {contact_file}")
        return
    
    if not Path(licensee_file).exists():
        logger.error(f"Licensee file not found: {licensee_file}")
        return
    
    # Generate new prospects
    try:
        new_prospects_df = generate_new_prospects(contact_file, licensee_file, output_file)
        logger.info(f"\nSuccess! New prospects file created: {output_file}")
        
        if len(new_prospects_df) > 0:
            logger.info("\nSample new prospects:")
            logger.info(new_prospects_df[['Name', 'Suburb', 'LGA', 'Licensee']].head(10).to_string())
        
    except Exception as e:
        logger.error(f"Error generating new prospects: {e}")
        raise


if __name__ == "__main__":
    main()
