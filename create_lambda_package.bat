@echo off
echo 📦 Creating minimal Lambda deployment package...

REM Clean up previous builds
if exist lambda_package rmdir /s /q lambda_package
if exist lambda_function.zip del lambda_function.zip

REM Create package directory
mkdir lambda_package
cd lambda_package

REM Install dependencies first (they go in root of Lambda)
echo 📥 Installing dependencies...
pip install -r ..\requirements_minimal.txt -t . --platform linux_x86_64 --only-binary=:all:

REM Copy main Lambda function (also goes in root for Lambda)
copy ..\lambda_function.py .

REM Clean up to reduce size
echo 🧹 Cleaning up package...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
for /d /r . %%d in (*.dist-info) do @if exist "%%d" rd /s /q "%%d"
for /d /r . %%d in (tests) do @if exist "%%d" rd /s /q "%%d"
for /d /r . %%d in (*.egg-info) do @if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc >nul 2>&1

REM Show directory structure
echo 📁 Package structure:
dir /b

REM Create ZIP file
echo 🗜️ Creating ZIP package...
powershell -command "Compress-Archive -Path * -DestinationPath ..\lambda_function.zip -Force"

cd ..
rmdir /s /q lambda_package

echo ✅ Lambda package created: lambda_function.zip
for %%I in (lambda_function.zip) do set FILESIZE=%%~zI
set /a FILESIZE_MB=%FILESIZE%/1024/1024
echo 📊 Package size: %FILESIZE_MB% MB

echo.
echo 🚀 Ready to upload to AWS Lambda!
echo.
echo 📋 Upload instructions:
echo 1. Add AWS Data Wrangler Lambda Layer (includes pandas):
echo    - Layer ARN: arn:aws:lambda:ap-southeast-2:336392948345:layer:AWSSDKPandas-Python313:4
echo    - Or search for "AWSSDKPandas-Python313" in Lambda console
echo 2. Upload lambda_function.zip to your function
echo 3. Set handler to: lambda_function.lambda_handler
echo 4. Set timeout to: 900 seconds (15 minutes)
echo 5. Set memory to: 512 MB
echo 6. Set environment variables:
echo    - S3_BUCKET: your-bucket-name
echo    - SNS_TOPIC_ARN: your-sns-topic (optional)
echo.
echo 📁 Expected Lambda structure after upload:
echo   /var/task/
echo   ├── lambda_function.py (your code)
echo   ├── requests/ (dependency)
echo   ├── urllib3/ (dependency)
echo   ├── certifi/ (dependency)
echo   └── ... (other dependencies)
echo.
echo ⚠️  IMPORTANT: Pandas layer is required for this function to work!
pause
