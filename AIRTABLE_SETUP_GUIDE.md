# Airtable Integration Setup Guide

## Step 1: Get Airtable API Credentials

### Create Personal Access Token:
1. Go to [Airtable Developer Hub](https://airtable.com/create/tokens)
2. Click **"Create new token"**
3. Name: `NSW Business Upload`
4. Scopes needed:
   - ✅ `data.records:write` (create records)
   - ✅ `data.records:read` (read existing records)
   - ✅ `schema.bases:read` (read base structure)
5. Select your base with business contacts
6. Copy the token (starts with `pat...`)

### Get Base ID:
1. Go to your Airtable base
2. Help → API documentation
3. Copy Base ID (starts with `app...`)

### Note Table Name:
- Your table name (e.g., "Businesses", "Contacts")

## Step 2: Configure Lambda Environment Variables

In AWS Lambda Console:
1. Go to your function: `lambda_function`
2. Configuration → Environment variables → Edit
3. Add these variables:

```
AIRTABLE_TOKEN=pat_xxxxxxxxxxxxxxxx
AIRTABLE_BASE_ID=appxxxxxxxxxxxxxxx
AIRTABLE_TABLE_NAME=Businesses
```

## Step 3: Test Integration

Run your Lambda function and check logs for:

```
[INFO] Uploading 25 businesses to Airtable...
[INFO] Uploading batch 1 (10 records)...
[INFO] Successfully uploaded batch (10 records)
[INFO] Uploading batch 2 (10 records)...
[INFO] Successfully uploaded batch (10 records)  
[INFO] Uploading batch 3 (5 records)...
[INFO] Successfully uploaded batch (5 records)
[INFO] Airtable upload complete: 25/25 records uploaded
[INFO] Airtable upload: 25 businesses uploaded
```

## Step 4: Verify in Airtable

Check your Airtable base - you should see new records with:
- ✅ Name, Address, Suburb, Postcode, LGA
- ✅ Licensee, Licensee ABN
- ✅ Notes: "New prospect from NSW premises list 2025-08-15"
- ✅ Empty fields ready for contact enrichment

## Features

### Automatic Batch Processing:
- Uploads in batches of 10 (Airtable limit)
- Continues on errors (doesn't fail entire upload)
- Logs detailed progress

### Data Cleaning:
- Removes empty/null values
- Formats data for Airtable
- Maintains your exact column structure

### Dual Storage:
- ✅ CSV backup in S3
- ✅ Direct upload to Airtable
- ✅ Detailed logging and reporting

## Troubleshooting

### Common Issues:
- **401 Unauthorized**: Check AIRTABLE_TOKEN
- **404 Not Found**: Check AIRTABLE_BASE_ID and table name
- **422 Unprocessable**: Column names don't match Airtable

### Test Command:
```bash
# Test with small dataset first
{
  "s3_bucket": "dna-licensee-data"
}
```
