@echo off
REM Deployment script for NSW Distillery Lambda function (Windows)

echo 🚀 Deploying NSW Distillery Monthly Workflow to AWS Lambda
echo ============================================================

REM Configuration
set FUNCTION_NAME=nsw-distillery-monthly-workflow
set RUNTIME=python3.11
set REGION=ap-southeast-2
set DEPLOYMENT_PACKAGE=lambda_deployment.zip

REM Check prerequisites
echo 📋 Checking prerequisites...

where aws >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ❌ AWS CLI not found. Please install and configure it first.
    pause
    exit /b 1
)

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ❌ Python not found. Please install Python 3.11 or later.
    pause
    exit /b 1
)

where terraform >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ⚠️  Terraform not found. Manual deployment will be needed.
    set TERRAFORM_AVAILABLE=false
) else (
    set TERRAFORM_AVAILABLE=true
)

REM Create deployment package
echo 📦 Creating deployment package...

REM Create temporary directory
if exist lambda_temp rmdir /s /q lambda_temp
mkdir lambda_temp
cd lambda_temp

REM Copy Python files
copy ..\lambda_monthly_workflow.py .
copy ..\generate_new_prospects.py .
copy ..\prospects_contact_lookup.py .
copy ..\business_lookup.py .

REM Install dependencies
echo 📥 Installing Python dependencies...
pip install -r ..\lambda_requirements.txt -t .

REM Remove unnecessary files to reduce package size
echo 🧹 Cleaning up package...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
for /d /r . %%d in (*.dist-info) do @if exist "%%d" rd /s /q "%%d"
for /d /r . %%d in (tests) do @if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc >nul 2>&1

REM Create ZIP package (using PowerShell)
echo 🗜️  Creating ZIP package...
powershell -command "Compress-Archive -Path * -DestinationPath ..\%DEPLOYMENT_PACKAGE% -Force"

cd ..
rmdir /s /q lambda_temp

echo ✅ Deployment package created: %DEPLOYMENT_PACKAGE%

REM Get file size
for %%I in (%DEPLOYMENT_PACKAGE%) do set FILESIZE=%%~zI
set /a FILESIZE_MB=%FILESIZE%/1024/1024
echo 📊 Package size: %FILESIZE_MB% MB

REM Deploy with Terraform if available
if "%TERRAFORM_AVAILABLE%"=="true" (
    echo.
    echo 🔧 Deploying with Terraform...
    
    REM Check if terraform.tfvars exists
    if not exist "terraform.tfvars" (
        echo 📝 Creating terraform.tfvars template...
        (
        echo aws_region = "ap-southeast-2"
        echo google_places_api_key = "YOUR_GOOGLE_PLACES_API_KEY_HERE"
        echo notification_email = "your-email@example.com"
        echo s3_bucket_name = "nsw-distillery-search-%RANDOM%"
        ) > terraform.tfvars
        echo ⚠️  Please edit terraform.tfvars with your actual values before continuing.
        echo    Then run: terraform init && terraform apply
        pause
        exit /b 0
    )
    
    REM Initialize and apply Terraform
    terraform init
    terraform plan
    
    echo.
    set /p confirm="🤔 Apply Terraform configuration? (y/N): "
    if /i "%confirm%"=="y" (
        terraform apply
        echo ✅ Infrastructure deployed successfully!
    ) else (
        echo ⏸️  Deployment cancelled. Run 'terraform apply' when ready.
    )
    
) else (
    echo.
    echo 📋 Manual deployment instructions:
    echo 1. Create S3 bucket for data storage
    echo 2. Create SNS topic for notifications
    echo 3. Create IAM role with S3 and SNS permissions
    echo 4. Upload %DEPLOYMENT_PACKAGE% to Lambda
    echo 5. Configure environment variables:
    echo    - S3_BUCKET: your-bucket-name
    echo    - SNS_TOPIC_ARN: your-sns-topic-arn
    echo    - GOOGLE_PLACES_API: your-api-key
    echo    - MAX_CONTACT_LOOKUPS: 100
    echo 6. Set up EventBridge rule to trigger monthly
)

echo.
echo 🎉 Deployment preparation complete!
echo.
echo 💡 Next steps:
echo 1. Confirm SNS email subscription
echo 2. Test the Lambda function manually
echo 3. Monitor CloudWatch logs
echo 4. Review first month's results
echo.
echo 💰 Expected monthly costs:
echo - Lambda: ~$1-5 (depending on execution time)
echo - S3: ~$1-2 (data storage)
echo - Google Places API: ~$32 per 1000 lookups
echo - SNS: ~$0.01 (notifications)
echo.
pause
