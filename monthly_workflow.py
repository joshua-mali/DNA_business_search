#!/usr/bin/env python3
"""
Monthly NSW Distillery Business Search Workflow

This script automates the monthly process of:
1. Comparing new month's licensee data with previous month
2. Identifying genuinely new businesses (not just data updates)
3. Running deduplication against existing contact database
4. Generating new prospects list
5. Creating monthly summary report

Usage:
    python monthly_workflow.py --current-month data/premises-list-Aug-2025.csv --previous-month data/premises-list-Jul-2025.csv
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from generate_new_prospects import (BusinessMatcher,
                                    convert_licensee_to_contact_format,
                                    filter_target_businesses)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def identify_new_licenses(current_month_df, previous_month_df):
    """
    Identify businesses that are genuinely new this month
    (not just data updates to existing licenses)
    """
    logger.info("Identifying new licenses from current month...")
    
    # Get license numbers from previous month
    previous_license_numbers = set(previous_month_df['Licence number'].dropna())
    
    # Find licenses in current month that weren't in previous month
    new_licenses_df = current_month_df[
        ~current_month_df['Licence number'].isin(previous_license_numbers)
    ].copy()
    
    logger.info(f"Found {len(new_licenses_df):,} completely new licenses this month")
    
    # Also check for licenses that changed status from non-trading to trading
    previous_non_trading = previous_month_df[
        (previous_month_df['Trading Status'] != 'Trading') |
        (previous_month_df['Status'] != 'Current')
    ]['Licence number'].dropna()
    
    current_trading = current_month_df[
        (current_month_df['Trading Status'] == 'Trading') &
        (current_month_df['Status'] == 'Current')
    ]
    
    newly_trading_df = current_trading[
        current_trading['Licence number'].isin(previous_non_trading)
    ].copy()
    
    logger.info(f"Found {len(newly_trading_df):,} licenses that became active/trading this month")
    
    # Combine new licenses and newly trading licenses
    all_new_df = pd.concat([new_licenses_df, newly_trading_df], ignore_index=True).drop_duplicates(subset=['Licence number'])
    
    logger.info(f"Total new business opportunities this month: {len(all_new_df):,}")
    
    return all_new_df


def generate_monthly_prospects(current_month_file, previous_month_file, contact_database_file, output_dir):
    """
    Complete monthly workflow to generate new prospects
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    logger.info("=" * 80)
    logger.info("STARTING MONTHLY PROSPECTS WORKFLOW")
    logger.info("=" * 80)
    
    # Load data files
    logger.info("Loading data files...")
    current_df = pd.read_csv(current_month_file, skiprows=3)
    previous_df = pd.read_csv(previous_month_file, skiprows=3)
    contact_df = pd.read_csv(contact_database_file)
    
    logger.info(f"Current month licensees: {len(current_df):,}")
    logger.info(f"Previous month licensees: {len(previous_df):,}")
    logger.info(f"Existing contacts: {len(contact_df):,}")
    
    # Step 1: Identify new licenses this month
    new_licenses_df = identify_new_licenses(current_df, previous_df)
    
    # Step 2: Filter for target business types
    target_new_licenses_df = filter_target_businesses(new_licenses_df)
    
    logger.info(f"New licenses matching target criteria: {len(target_new_licenses_df):,}")
    
    # Step 3: Remove duplicates against existing contact database
    logger.info("Running deduplication against existing contact database...")
    matcher = BusinessMatcher(similarity_threshold=85)
    
    monthly_prospects = []
    duplicates_found = []
    
    for idx, licensee_row in target_new_licenses_df.iterrows():
        is_duplicate, match_reason = matcher.find_matches(contact_df, licensee_row)
        
        if is_duplicate:
            duplicates_found.append({
                'Name': licensee_row.get('Licence name'),
                'Suburb': licensee_row.get('Suburb'),
                'Licensee': licensee_row.get('Licensee'),
                'Match_Reason': match_reason
            })
        else:
            new_prospect = convert_licensee_to_contact_format(licensee_row)
            monthly_prospects.append(new_prospect)
    
    # Step 4: Create output files
    prospects_df = pd.DataFrame(monthly_prospects)
    duplicates_df = pd.DataFrame(duplicates_found)
    
    # Save prospects file
    prospects_file = output_dir / f"Monthly_Prospects_{timestamp}.csv"
    prospects_df.to_csv(prospects_file, index=False)
    
    # Save duplicates report
    duplicates_file = output_dir / f"Monthly_Duplicates_{timestamp}.csv"
    duplicates_df.to_csv(duplicates_file, index=False)
    
    # Step 5: Generate summary report
    generate_monthly_report(
        current_df, previous_df, contact_df, new_licenses_df, 
        target_new_licenses_df, prospects_df, duplicates_df,
        matcher, output_dir, timestamp
    )
    
    return prospects_df, duplicates_df


def generate_monthly_report(current_df, previous_df, contact_df, new_licenses_df, 
                          target_new_licenses_df, prospects_df, duplicates_df, 
                          matcher, output_dir, timestamp):
    """
    Generate comprehensive monthly report
    """
    report_file = output_dir / f"Monthly_Report_{timestamp}.txt"
    
    report_content = f"""
NSW DISTILLERY BUSINESS SEARCH - MONTHLY REPORT
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
================================================================================

DATA SUMMARY:
- Current month total licensees: {len(current_df):,}
- Previous month total licensees: {len(previous_df):,}
- Net change in licensees: {len(current_df) - len(previous_df):+,}
- Existing contact database size: {len(contact_df):,}

NEW BUSINESS IDENTIFICATION:
- Completely new licenses this month: {len(new_licenses_df):,}
- New licenses matching target criteria: {len(target_new_licenses_df):,}
- Target business filtering ratio: {len(target_new_licenses_df)/len(new_licenses_df)*100:.1f}%

DEDUPLICATION RESULTS:
- Prospects after deduplication: {len(prospects_df):,}
- Duplicates found and removed: {len(duplicates_df):,}
- Deduplication effectiveness: {len(duplicates_df)/(len(duplicates_df)+len(prospects_df))*100:.1f}%

MATCHING METHOD BREAKDOWN:
- ABN matches: {matcher.abn_matches:,}
- Name + Suburb matches: {matcher.name_suburb_matches:,}
- Licensee + Suburb matches: {matcher.licensee_suburb_matches:,}
- Address matches: {matcher.address_matches:,}

BUSINESS TYPE BREAKDOWN (New Prospects):
"""
    
    if len(prospects_df) > 0:
        # Analyze business types in prospects
        business_types = {}
        for _, row in target_new_licenses_df.iterrows():
            if row.get('Licence name') in prospects_df['Name'].values:
                btype = row.get('Business type', 'Unknown')
                business_types[btype] = business_types.get(btype, 0) + 1
        
        for btype, count in sorted(business_types.items(), key=lambda x: x[1], reverse=True):
            report_content += f"- {btype}: {count:,} prospects\n"
    
    report_content += f"""

GEOGRAPHIC DISTRIBUTION (Top 10 LGAs):
"""
    
    if len(prospects_df) > 0:
        lga_counts = prospects_df['LGA'].value_counts().head(10)
        for lga, count in lga_counts.items():
            report_content += f"- {lga}: {count:,} prospects\n"
    
    report_content += f"""

RECOMMENDATIONS FOR CONTACT RESEARCH:
- Total new prospects to research: {len(prospects_df):,}
- Estimated research time (5 min/business): {len(prospects_df) * 5 / 60:.1f} hours
- Priority: Focus on restaurants and hotels first
- Tools: Use Google Places API, website scraping, social media lookup

FILES GENERATED:
- New prospects: Monthly_Prospects_{timestamp}.csv
- Duplicates report: Monthly_Duplicates_{timestamp}.csv
- Summary report: Monthly_Report_{timestamp}.txt

NEXT MONTH PREPARATION:
1. Update contact database with any new contacts found
2. Download next month's premises list from NSW Government
3. Run this workflow again with updated files
4. Compare results month-over-month for trend analysis

================================================================================
End of Report
"""
    
    # Write report to file
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    # Also print summary to console
    logger.info("=" * 80)
    logger.info("MONTHLY WORKFLOW COMPLETE")
    logger.info("=" * 80)
    logger.info(f"New prospects identified: {len(prospects_df):,}")
    logger.info(f"Duplicates removed: {len(duplicates_df):,}")
    logger.info(f"Files saved to: {output_dir}")
    logger.info(f"Report saved to: {report_file}")
    
    if len(prospects_df) > 0:
        logger.info("\nSample new prospects:")
        sample_prospects = prospects_df[['Name', 'Suburb', 'LGA', 'Licensee']].head(5)
        for _, row in sample_prospects.iterrows():
            logger.info(f"  - {row['Name']} in {row['Suburb']}, {row['LGA']}")


def main():
    """
    Main function with command line interface
    """
    parser = argparse.ArgumentParser(description='Monthly NSW Business Search Workflow')
    parser.add_argument('--current-month', required=True, 
                       help='Path to current month premises list CSV')
    parser.add_argument('--previous-month', required=True,
                       help='Path to previous month premises list CSV')
    parser.add_argument('--contact-database', 
                       default='data/Businesses up to Sep 2024.csv',
                       help='Path to existing contact database CSV')
    parser.add_argument('--output-dir', default='monthly_output',
                       help='Directory to save output files')
    
    args = parser.parse_args()
    
    # Validate input files
    for file_path in [args.current_month, args.previous_month, args.contact_database]:
        if not Path(file_path).exists():
            logger.error(f"File not found: {file_path}")
            return 1
    
    try:
        prospects_df, duplicates_df = generate_monthly_prospects(
            args.current_month,
            args.previous_month, 
            args.contact_database,
            args.output_dir
        )
        
        logger.info(f"\nSuccess! Found {len(prospects_df):,} new prospects this month.")
        return 0
        
    except Exception as e:
        logger.error(f"Error in monthly workflow: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
