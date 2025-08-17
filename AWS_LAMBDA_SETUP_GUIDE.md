# AWS Lambda Setup Guide for NSW Distillery Monthly Workflow (Windows)

## 🎯 **Overview**
This guide will help you deploy the NSW Distillery business search as a fully automated AWS Lambda function that runs monthly.

## 📋 **Prerequisites**

### **1. AWS Account & CLI**
```powershell
# Install AWS CLI v2 for Windows
# Download from: https://awscli.amazonaws.com/AWSCLIV2.msi

# Configure AWS credentials
aws configure
```

### **2. Python Environment**
```powershell
# Ensure Python 3.11 is installed
python --version

# Activate your virtual environment
.venv\Scripts\activate
```

### **3. Terraform (Optional but Recommended)**
```powershell
# Download from: https://www.terraform.io/downloads
# Add to PATH environment variable
terraform --version
```

## 🚀 **Deployment Options**

### **Option A: Automated Deployment (Recommended)**

#### **1. Run the deployment script:**
```cmd
deploy_lambda.bat
```

#### **2. Configure your settings:**
Edit `terraform.tfvars` when prompted:
```hcl
aws_region = "ap-southeast-2"
google_places_api_key = "your_actual_google_api_key"
notification_email = "your-email@company.com"
s3_bucket_name = "nsw-distillery-search-12345"
```

#### **3. Deploy infrastructure:**
```powershell
terraform init
terraform apply
```

### **Option B: Manual AWS Console Setup**

#### **1. Create S3 Bucket**
- Bucket name: `nsw-distillery-search-[unique-id]`
- Region: `ap-southeast-2` (Sydney)
- Enable versioning
- Enable default encryption

#### **2. Create SNS Topic**
- Topic name: `nsw-distillery-search-notifications`
- Add email subscription for notifications

#### **3. Create IAM Role**
- Role name: `nsw-distillery-lambda-role`
- Attach policies:
  - `AWSLambdaBasicExecutionRole`
  - Custom policy for S3 and SNS access

#### **4. Create Lambda Function**
- Function name: `nsw-distillery-monthly-workflow`
- Runtime: `Python 3.11`
- Memory: `1024 MB`
- Timeout: `15 minutes`
- Upload: `lambda_deployment.zip`

#### **5. Set Environment Variables**
```
S3_BUCKET = your-bucket-name
SNS_TOPIC_ARN = arn:aws:sns:ap-southeast-2:account:topic-name
GOOGLE_PLACES_API = your-google-api-key
MAX_CONTACT_LOOKUPS = 100
```

#### **6. Create EventBridge Rule**
- Rule name: `nsw-distillery-monthly-trigger`
- Schedule: `cron(0 9 5 * ? *)` (9 AM on 5th of every month)
- Target: Your Lambda function

## 💰 **Cost Breakdown**

### **Monthly AWS Costs:**
- **Lambda:** $1-5 (15 min execution monthly)
- **S3:** $1-2 (data storage ~100MB)
- **SNS:** $0.01 (email notifications)
- **EventBridge:** $0.01 (monthly trigger)

### **Google Places API Costs:**
- **Text Search:** $32 per 1,000 requests
- **Place Details:** First 10,000 free, then $17 per 1,000
- **Monthly estimate:** $30-50 for ~1,000 new businesses

### **Total Monthly Cost:** ~$35-60

## 📊 **What the Lambda Function Does**

### **Automated Monthly Process:**
1. **Downloads** current and previous month NSW premises lists
2. **Identifies** new businesses (licenses not in previous month)
3. **Filters** for target business types (restaurants, bars, hotels)
4. **Deduplicates** against existing contact database
5. **Runs contact lookup** using Google Places API
6. **Saves results** to S3 in separate files:
   - `contacts_found_*.csv` - Ready for Airtable upload
   - `no_contacts_*.csv` - For manual/AI processing
7. **Updates** master contact database
8. **Sends email notification** with summary report

### **Expected Output (Monthly):**
- **New prospects:** 50-200 businesses
- **Email success rate:** 60-70%
- **Processing time:** 10-15 minutes
- **Ready for Airtable:** ~100-140 contacts
- **Manual follow-up needed:** ~30-60 businesses

## 🔧 **Configuration Options**

### **Adjust Processing Volume:**
```python
# In terraform.tfvars or Lambda environment variables
MAX_CONTACT_LOOKUPS = 50   # Reduce for lower costs
MAX_CONTACT_LOOKUPS = 200  # Increase for more coverage
```

### **Modify Schedule:**
```cron
# Current: 9 AM on 5th of month
cron(0 9 5 * ? *)

# Alternative: 6 AM on 1st of month
cron(0 6 1 * ? *)

# Alternative: Weekly on Mondays
cron(0 9 ? * MON *)
```

### **Filter Business Types:**
Edit `filter_target_businesses()` in `generate_new_prospects.py` to adjust which business types are targeted.

## 📋 **Testing & Validation**

### **1. Test Lambda Function:**
```json
{
  "test": true,
  "max_lookups": 5
}
```

### **2. Monitor CloudWatch Logs:**
- Navigate to CloudWatch > Log Groups
- Find `/aws/lambda/nsw-distillery-monthly-workflow`
- Monitor execution logs

### **3. Check S3 Output:**
- Verify files are created in your S3 bucket
- Download and review CSV files

### **4. Validate Notifications:**
- Confirm SNS email subscription
- Check for monthly summary emails

## 🚨 **Troubleshooting**

### **Common Issues:**

#### **1. NSW Data Download Fails:**
- Check if NSW government changed URL format
- Update `premises_list_url_pattern` in Lambda code

#### **2. Google API Quota Exceeded:**
- Reduce `MAX_CONTACT_LOOKUPS`
- Monitor usage in Google Cloud Console

#### **3. Lambda Timeout:**
- Increase timeout to 15 minutes
- Reduce processing batch size

#### **4. S3 Permission Errors:**
- Verify IAM role has S3 read/write permissions
- Check bucket policy

## 📈 **Monitoring & Optimization**

### **Key Metrics to Track:**
- **Lambda duration** (keep under 15 minutes)
- **API success rate** (target >80%)
- **Cost per prospect** (target <$0.50)
- **Email deliverability** (target >60%)

### **Monthly Review Process:**
1. **Download** contacts from S3
2. **Upload** to Airtable
3. **Review** failed lookups for patterns
4. **Adjust** parameters based on performance
5. **Update** contact database with new findings

## 🎉 **Benefits of Lambda Deployment**

✅ **Fully Automated** - No manual intervention needed
✅ **Scalable** - Handles varying monthly volumes  
✅ **Cost Effective** - Pay only for usage
✅ **Reliable** - AWS infrastructure reliability
✅ **Monitoring** - Built-in CloudWatch logging
✅ **Notifications** - Automatic email reports
✅ **Data Persistence** - S3 storage with versioning

Your distillery client will receive automated monthly prospect lists without any manual work from you! 🎯
