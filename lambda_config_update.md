# Lambda Function Configuration Update

## Current Issue
- Function is timing out after 3 seconds
- Memory is set to 128 MB (too low)

## Required Changes

### 1. Update Timeout
- **Current**: 3 seconds (default)
- **Required**: 300 seconds (5 minutes)

### 2. Update Memory
- **Current**: 128 MB 
- **Required**: 256 MB

## How to Update via AWS Console

1. Go to AWS Lambda Console: https://ap-southeast-2.console.aws.amazon.com/lambda/home?region=ap-southeast-2
2. Click on your function: `lambda_function`
3. Go to **Configuration** tab
4. Click **General configuration** → **Edit**
5. Update:
   - **Timeout**: `5 min 0 sec`
   - **Memory**: `256 MB`
6. Click **Save**

## Alternative: Update via AWS CLI (if available)
```bash
aws lambda update-function-configuration \
  --function-name lambda_function \
  --timeout 300 \
  --memory-size 256 \
  --region ap-southeast-2
```

## Test After Update
Run the function again - it should now have enough time to download the June file.
