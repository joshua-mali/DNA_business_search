#!/usr/bin/env python3
"""
Data Structure Analysis Script for NSW Distillery Business Search

This script analyzes the structure of:
1. Contact details database (businesses that were manually researched)
2. NSW Government licensee data (premises list)

The goal is to understand the data structure to automate the process of
finding new businesses and their contact details.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_contact_details_data(file_path):
    """
    Analyze the structure of the contact details database
    """
    logger.info("Analyzing contact details data structure...")
    
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)
        
        print("=" * 80)
        print("CONTACT DETAILS DATABASE ANALYSIS")
        print("=" * 80)
        
        # Basic info
        print(f"Total records: {len(df)}")
        print(f"Total columns: {len(df.columns)}")
        print(f"File size: {Path(file_path).stat().st_size / (1024*1024):.2f} MB")
        
        # Column information
        print("\nColumn Information:")
        print("-" * 50)
        for i, col in enumerate(df.columns, 1):
            non_null_count = df[col].notna().sum()
            null_count = df[col].isna().sum()
            unique_count = df[col].nunique()
            print(f"{i:2d}. {col}")
            print(f"    Non-null: {non_null_count:,} ({non_null_count/len(df)*100:.1f}%)")
            print(f"    Null: {null_count:,} ({null_count/len(df)*100:.1f}%)")
            print(f"    Unique values: {unique_count:,}")
            
            # Show sample values for key columns
            if col.lower() in ['name', 'licensee', 'address', 'suburb', 'email address', 'phone number']:
                sample_values = df[col].dropna().head(3).tolist()
                print(f"    Sample values: {sample_values}")
            print()
        
        # Data quality analysis
        print("\nData Quality Analysis:")
        print("-" * 50)
        
        # Check for businesses with contact information
        has_email = df['Email Address'].notna().sum()
        has_phone = df['Phone Number'].notna().sum()
        has_facebook = df['Facebook Link'].notna().sum()
        has_instagram = df['Instagram link'].notna().sum()
        
        print(f"Businesses with email: {has_email:,} ({has_email/len(df)*100:.1f}%)")
        print(f"Businesses with phone: {has_phone:,} ({has_phone/len(df)*100:.1f}%)")
        print(f"Businesses with Facebook: {has_facebook:,} ({has_facebook/len(df)*100:.1f}%)")
        print(f"Businesses with Instagram: {has_instagram:,} ({has_instagram/len(df)*100:.1f}%)")
        
        # Businesses with any contact method
        has_any_contact = df[['Email Address', 'Phone Number', 'Facebook Link', 'Instagram link']].notna().any(axis=1).sum()
        print(f"Businesses with any contact method: {has_any_contact:,} ({has_any_contact/len(df)*100:.1f}%)")
        
        # Geographic distribution
        print(f"\nGeographic Distribution:")
        print(f"Unique LGAs: {df['LGA'].nunique()}")
        print(f"Unique postcodes: {df['Postcode'].nunique()}")
        print(f"Unique suburbs: {df['Suburb'].nunique()}")
        
        # Top LGAs
        print("\nTop 10 LGAs by business count:")
        lga_counts = df['LGA'].value_counts().head(10)
        for lga, count in lga_counts.items():
            print(f"  {lga}: {count:,} businesses")
        
        # Email activity analysis
        email_cols = ['Date email 1 sent', 'Date email 2 sent', 'Date email 3 sent']
        for col in email_cols:
            if col in df.columns:
                sent_count = df[col].notna().sum()
                print(f"\n{col}: {sent_count:,} businesses contacted")
        
        return df
        
    except Exception as e:
        logger.error(f"Error analyzing contact details data: {e}")
        return None

def analyze_licensee_data(file_path):
    """
    Analyze the structure of the NSW Government licensee data
    """
    logger.info("Analyzing NSW licensee data structure...")
    
    try:
        # Read the CSV file, skipping the header rows
        df = pd.read_csv(file_path, skiprows=3)  # Skip the summary rows at the top
        
        print("\n" + "=" * 80)
        print("NSW GOVERNMENT LICENSEE DATA ANALYSIS")
        print("=" * 80)
        
        # Basic info
        print(f"Total records: {len(df)}")
        print(f"Total columns: {len(df.columns)}")
        print(f"File size: {Path(file_path).stat().st_size / (1024*1024):.2f} MB")
        
        # Column information
        print("\nColumn Information:")
        print("-" * 50)
        for i, col in enumerate(df.columns, 1):
            non_null_count = df[col].notna().sum()
            null_count = df[col].isna().sum()
            unique_count = df[col].nunique()
            print(f"{i:2d}. {col}")
            print(f"    Non-null: {non_null_count:,} ({non_null_count/len(df)*100:.1f}%)")
            print(f"    Null: {null_count:,} ({null_count/len(df)*100:.1f}%)")
            print(f"    Unique values: {unique_count:,}")
            
            # Show sample values for key columns
            if col.lower() in ['licence name', 'licensee', 'address', 'suburb', 'business type', 'licence type']:
                sample_values = df[col].dropna().head(3).tolist()
                print(f"    Sample values: {sample_values}")
            print()
        
        # License analysis
        print("\nLicense Type Distribution:")
        print("-" * 50)
        license_types = df['Licence type'].value_counts()
        for license_type, count in license_types.items():
            print(f"  {license_type}: {count:,} licenses ({count/len(df)*100:.1f}%)")
        
        # Business type analysis
        print("\nBusiness Type Distribution:")
        print("-" * 50)
        business_types = df['Business type'].value_counts().head(15)
        for business_type, count in business_types.items():
            print(f"  {business_type}: {count:,} businesses ({count/len(df)*100:.1f}%)")
        
        # Status analysis
        print("\nLicense Status Distribution:")
        print("-" * 50)
        status_counts = df['Status'].value_counts()
        for status, count in status_counts.items():
            print(f"  {status}: {count:,} licenses ({count/len(df)*100:.1f}%)")
        
        # Trading status analysis
        print("\nTrading Status Distribution:")
        print("-" * 50)
        trading_status_counts = df['Trading Status'].value_counts()
        for status, count in trading_status_counts.items():
            print(f"  {status}: {count:,} licenses ({count/len(df)*100:.1f}%)")
        
        # Geographic distribution
        print(f"\nGeographic Distribution:")
        print(f"Unique LGAs: {df['LGA'].nunique()}")
        print(f"Unique postcodes: {df['Postcode'].nunique()}")
        print(f"Unique suburbs: {df['Suburb'].nunique()}")
        
        # Top LGAs
        print("\nTop 10 LGAs by license count:")
        lga_counts = df['LGA'].value_counts().head(10)
        for lga, count in lga_counts.items():
            print(f"  {lga}: {count:,} licenses")
        
        # Licensee type analysis
        print("\nLicensee Type Distribution:")
        print("-" * 50)
        licensee_types = df['Licensee Type'].value_counts()
        for licensee_type, count in licensee_types.items():
            print(f"  {licensee_type}: {count:,} licensees ({count/len(df)*100:.1f}%)")
        
        return df
        
    except Exception as e:
        logger.error(f"Error analyzing licensee data: {e}")
        return None

def compare_datasets(contact_df, licensee_df):
    """
    Compare the two datasets to identify potential matching fields
    """
    if contact_df is None or licensee_df is None:
        logger.error("Cannot compare datasets - one or both failed to load")
        return
    
    print("\n" + "=" * 80)
    print("DATASET COMPARISON AND MATCHING ANALYSIS")
    print("=" * 80)
    
    # Compare key fields that could be used for matching
    print("\nPotential Matching Fields:")
    print("-" * 50)
    
    # Business names
    print("1. Business Names:")
    print(f"   Contact DB - 'Name' field: {contact_df['Name'].nunique():,} unique names")
    print(f"   Licensee DB - 'Licence name' field: {licensee_df['Licence name'].nunique():,} unique names")
    
    # Licensee names
    print("\n2. Licensee/Owner Names:")
    print(f"   Contact DB - 'Licensee' field: {contact_df['Licensee'].nunique():,} unique licensees")
    print(f"   Licensee DB - 'Licensee' field: {licensee_df['Licensee'].nunique():,} unique licensees")
    
    # ABN matching potential
    contact_abn_count = contact_df['Licensee ABN'].notna().sum() if 'Licensee ABN' in contact_df.columns else 0
    licensee_abn_count = licensee_df['Licensee ABN'].notna().sum() if 'Licensee ABN' in licensee_df.columns else 0
    print(f"\n3. ABN Matching:")
    print(f"   Contact DB - ABNs available: {contact_abn_count:,}")
    print(f"   Licensee DB - ABNs available: {licensee_abn_count:,}")
    
    # Geographic matching
    print(f"\n4. Geographic Matching:")
    contact_suburbs = set(contact_df['Suburb'].dropna().str.upper())
    licensee_suburbs = set(licensee_df['Suburb'].dropna().str.upper())
    common_suburbs = contact_suburbs.intersection(licensee_suburbs)
    print(f"   Contact DB suburbs: {len(contact_suburbs):,}")
    print(f"   Licensee DB suburbs: {len(licensee_suburbs):,}")
    print(f"   Common suburbs: {len(common_suburbs):,}")
    
    # Check for potential matches by name similarity (basic check)
    print(f"\n5. Basic Name Matching Analysis:")
    contact_names = set(contact_df['Name'].dropna().str.upper())
    licensee_names = set(licensee_df['Licence name'].dropna().str.upper())
    exact_matches = contact_names.intersection(licensee_names)
    print(f"   Exact name matches found: {len(exact_matches)}")
    
    if len(exact_matches) > 0:
        print("   Sample exact matches:")
        for match in list(exact_matches)[:5]:
            print(f"     - {match}")

def generate_insights_and_recommendations():
    """
    Generate insights and recommendations for the automation process
    """
    print("\n" + "=" * 80)
    print("INSIGHTS AND RECOMMENDATIONS FOR AUTOMATION")
    print("=" * 80)
    
    recommendations = [
        "1. MATCHING STRATEGY:",
        "   - Primary: Use ABN matching where available (most reliable)",
        "   - Secondary: Combine business name + suburb + licensee name for fuzzy matching",
        "   - Tertiary: Address-based matching as fallback",
        "",
        "2. TARGET BUSINESS TYPES:",
        "   - Focus on 'Restaurant', 'Hotel', 'Club', 'Pub' license types",
        "   - Filter for 'Current' status and 'Trading' status only",
        "   - Exclude certain business types (e.g., 'Bottle shops & delivery')",
        "",
        "3. CONTACT DISCOVERY AUTOMATION:",
        "   - Use Google Places API for basic business information",
        "   - Scrape business websites for contact details",
        "   - Use social media APIs for Facebook/Instagram presence",
        "   - Implement email pattern detection (info@, contact@, etc.)",
        "",
        "4. MONTHLY PROCESSING WORKFLOW:",
        "   - Compare new month's licensee data with previous month",
        "   - Identify new licenses using licence number or start date",
        "   - Filter new businesses by target criteria",
        "   - Run automated contact discovery for new businesses only",
        "   - Generate report of new prospects with confidence scores",
        "",
        "5. DATA QUALITY IMPROVEMENTS:",
        "   - Standardize business name formatting for better matching",
        "   - Implement address normalization",
        "   - Add confidence scoring for matches",
        "   - Track success rates of different matching methods"
    ]
    
    for recommendation in recommendations:
        print(recommendation)

def main():
    """
    Main function to run the analysis
    """
    print("Starting Data Structure Analysis for NSW Distillery Business Search")
    print("=" * 80)
    
    # Define file paths
    contact_details_file = "data/Businesses up to Sep 2024.csv"
    licensee_data_file = "data/premises-list-Jul-2025 - premises list.csv"
    
    # Analyze both datasets
    contact_df = analyze_contact_details_data(contact_details_file)
    licensee_df = analyze_licensee_data(licensee_data_file)
    
    # Compare datasets
    compare_datasets(contact_df, licensee_df)
    
    # Generate recommendations
    generate_insights_and_recommendations()
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("Next steps:")
    print("1. Review the analysis above")
    print("2. Implement the matching algorithm based on recommendations")
    print("3. Set up monthly automated processing")
    print("4. Test with a small subset before full automation")

if __name__ == "__main__":
    main()
