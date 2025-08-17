# Airtable Upload Script

This script processes CSV files from the `data/upload/` folder, splits email addresses into separate columns, and uploads the data to Airtable.

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r airtable_requirements.txt
```

### 2. Create Environment File

Create a `.env` file in the project root with your Airtable credentials:

```bash
# Copy the template
cp env_template.txt .env
```

Then edit `.env` with your actual values:

```
AIRTABLE_API_TOKEN=your_airtable_api_token_here
AIRTABLE_BASE_ID=your_airtable_base_id_here
AIRTABLE_TABLE_NAME=your_table_name_here
TEST_MODE=False
```

### 3. Get Your Airtable Credentials

#### API Token
1. Go to https://airtable.com/create/tokens
2. Create a new personal access token
3. Give it appropriate permissions (data.records:write, data.records:read, schema.bases:read)

#### Base ID
1. Go to your Airtable base
2. Click "Help" → "API documentation"
3. Your Base ID will be shown (starts with "app...")

#### Table Name
- Use the exact name of your table in Airtable (case-sensitive)

## Usage

### Basic Usage

```bash
python airtable_upload_script.py
```

This will:
1. Process all CSV files in `data/upload/`
2. Split emails from "Email Address" and "Additional Email" columns into email_1, email_2, email_3, email_4, email_5
3. Upload all records to your Airtable

### Test Mode

Set `TEST_MODE=True` in your `.env` file to see what would be uploaded without actually uploading:

```bash
# In .env file
TEST_MODE=True
```

## Data Processing

The script performs the following transformations:

### Email Processing
- Extracts email addresses from "Email Address" and "Additional Email" columns
- Uses regex to find valid email patterns
- Splits them into separate columns: email_1, email_2, email_3, email_4, email_5
- Removes duplicates while preserving order

### Fields Mapped to Airtable
- Name
- Address  
- Suburb
- Postcode
- LGA
- Licensee
- Licensee ABN
- Facebook Link
- Instagram link
- Phone Number
- Source File (automatically added)
- email_1, email_2, email_3, email_4, email_5 (split from original email columns)

## Logging

The script creates an `airtable_upload.log` file with detailed information about the upload process.

## Error Handling

- Continues processing even if individual records fail
- Logs all errors for review
- Uses batch uploads with rate limiting to respect Airtable API limits
- Validates environment variables before starting

## File Structure

```
data/upload/
├── Contacts_Found_20250817_0644.csv
├── No_Contacts_Found_20250817_0644.csv
└── ... (other CSV files)
```

All CSV files in this folder will be processed automatically.

## Troubleshooting

### Common Issues

1. **Missing .env file**: Make sure you've created a `.env` file with your credentials
2. **Invalid API token**: Verify your token has the correct permissions
3. **Table not found**: Check that your table name matches exactly (case-sensitive)
4. **Rate limiting**: The script includes automatic rate limiting, but if you encounter issues, the uploads are batched

### Checking Logs

Review `airtable_upload.log` for detailed information about what was processed and any errors encountered.
