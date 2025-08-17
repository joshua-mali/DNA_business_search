@echo off
echo 📦 Creating test Lambda package...

REM Clean up
if exist test_package rmdir /s /q test_package
if exist lambda_test.zip del lambda_test.zip

REM Create package
mkdir test_package
cd test_package

REM Install dependencies
echo 📥 Installing dependencies...
pip install -r ..\requirements_test.txt -t . --platform linux_x86_64 --only-binary=:all:

REM Copy Lambda function
copy ..\lambda_function.py .

REM Clean up
echo 🧹 Cleaning up...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
for /d /r . %%d in (*.dist-info) do @if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc >nul 2>&1

REM Show structure
echo 📁 Package contents:
dir /b

REM Create ZIP
echo 🗜️ Creating ZIP...
powershell -command "Compress-Archive -Path * -DestinationPath ..\lambda_test.zip -Force"

cd ..
rmdir /s /q test_package

echo ✅ Test package created: lambda_test.zip
for %%I in (lambda_test.zip) do set FILESIZE=%%~zI
set /a FILESIZE_KB=%FILESIZE%/1024
echo 📊 Package size: %FILESIZE_KB% KB

echo.
echo 🚀 Ready to test!
echo.
echo 📋 Test instructions:
echo 1. Upload lambda_test.zip to your Lambda function
echo 2. Set handler to: lambda_function.lambda_handler
echo 3. Set timeout to: 300 seconds (5 minutes) ⚠️ IMPORTANT!
echo 4. Set memory to: 256 MB (for Excel processing)
echo 5. Set environment variable: S3_BUCKET=your-bucket-name
echo 6. Test with this event:
echo {
echo   "s3_bucket": "your-bucket-name"
echo }
echo.
echo ⚠️ CRITICAL: Must increase timeout from 3 seconds to 300 seconds!
echo.
pause
