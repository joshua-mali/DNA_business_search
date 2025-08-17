#!/bin/bash
# Deployment script for NSW Distillery Lambda function

set -e  # Exit on any error

echo "🚀 Deploying NSW Distillery Monthly Workflow to AWS Lambda"
echo "============================================================"

# Configuration
FUNCTION_NAME="nsw-distillery-monthly-workflow"
RUNTIME="python3.11"
REGION="ap-southeast-2"
DEPLOYMENT_PACKAGE="lambda_deployment.zip"

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install and configure it first."
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.11 or later."
    exit 1
fi

if ! command -v terraform &> /dev/null; then
    echo "⚠️  Terraform not found. Manual deployment will be needed."
    TERRAFORM_AVAILABLE=false
else
    TERRAFORM_AVAILABLE=true
fi

# Create deployment package
echo "📦 Creating deployment package..."

# Create temporary directory
rm -rf lambda_temp
mkdir lambda_temp
cd lambda_temp

# Copy Python files
cp ../lambda_monthly_workflow.py .
cp ../generate_new_prospects.py .
cp ../prospects_contact_lookup.py .
cp ../business_lookup.py .

# Install dependencies
echo "📥 Installing Python dependencies..."
pip install -r ../lambda_requirements.txt -t .

# Remove unnecessary files to reduce package size
echo "🧹 Cleaning up package..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Create ZIP package
echo "🗜️  Creating ZIP package..."
zip -r ../$DEPLOYMENT_PACKAGE . -q

cd ..
rm -rf lambda_temp

echo "✅ Deployment package created: $DEPLOYMENT_PACKAGE"
echo "📊 Package size: $(du -h $DEPLOYMENT_PACKAGE | cut -f1)"

# Deploy with Terraform if available
if [ "$TERRAFORM_AVAILABLE" = true ]; then
    echo ""
    echo "🔧 Deploying with Terraform..."
    
    # Check if terraform.tfvars exists
    if [ ! -f "terraform.tfvars" ]; then
        echo "📝 Creating terraform.tfvars template..."
        cat > terraform.tfvars << EOF
aws_region = "ap-southeast-2"
google_places_api_key = "YOUR_GOOGLE_PLACES_API_KEY_HERE"
notification_email = "your-email@example.com"
s3_bucket_name = "nsw-distillery-search-\$(date +%s)"  # Unique bucket name
EOF
        echo "⚠️  Please edit terraform.tfvars with your actual values before continuing."
        echo "   Then run: terraform init && terraform apply"
        exit 0
    fi
    
    # Initialize and apply Terraform
    terraform init
    terraform plan
    
    echo ""
    read -p "🤔 Apply Terraform configuration? (y/N): " confirm
    if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
        terraform apply
        echo "✅ Infrastructure deployed successfully!"
    else
        echo "⏸️  Deployment cancelled. Run 'terraform apply' when ready."
    fi
    
else
    echo ""
    echo "📋 Manual deployment instructions:"
    echo "1. Create S3 bucket for data storage"
    echo "2. Create SNS topic for notifications"
    echo "3. Create IAM role with S3 and SNS permissions"
    echo "4. Upload $DEPLOYMENT_PACKAGE to Lambda"
    echo "5. Configure environment variables:"
    echo "   - S3_BUCKET: your-bucket-name"
    echo "   - SNS_TOPIC_ARN: your-sns-topic-arn"
    echo "   - GOOGLE_PLACES_API: your-api-key"
    echo "   - MAX_CONTACT_LOOKUPS: 100"
    echo "6. Set up EventBridge rule to trigger monthly"
fi

echo ""
echo "🎉 Deployment preparation complete!"
echo ""
echo "💡 Next steps:"
echo "1. Confirm SNS email subscription"
echo "2. Test the Lambda function manually"
echo "3. Monitor CloudWatch logs"
echo "4. Review first month's results"
echo ""
echo "💰 Expected monthly costs:"
echo "- Lambda: ~\$1-5 (depending on execution time)"
echo "- S3: ~\$1-2 (data storage)"
echo "- Google Places API: ~\$32 per 1000 lookups"
echo "- SNS: ~\$0.01 (notifications)"
echo ""
