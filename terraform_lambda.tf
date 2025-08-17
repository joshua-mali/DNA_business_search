# Terraform configuration for NSW Distillery Lambda function
# This creates all the AWS resources needed for the monthly workflow

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-southeast-2"  # Sydney region
}

variable "google_places_api_key" {
  description = "Google Places API key"
  type        = string
  sensitive   = true
}

variable "notification_email" {
  description = "Email address for notifications"
  type        = string
}

variable "s3_bucket_name" {
  description = "S3 bucket name for data storage"
  type        = string
  default     = "nsw-distillery-search"
}

# S3 Bucket for data storage
resource "aws_s3_bucket" "distillery_data" {
  bucket = var.s3_bucket_name
}

resource "aws_s3_bucket_versioning" "distillery_data_versioning" {
  bucket = aws_s3_bucket.distillery_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "distillery_data_encryption" {
  bucket = aws_s3_bucket.distillery_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# SNS Topic for notifications
resource "aws_sns_topic" "distillery_notifications" {
  name = "nsw-distillery-search-notifications"
}

resource "aws_sns_topic_subscription" "email_notification" {
  topic_arn = aws_sns_topic.distillery_notifications.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "nsw-distillery-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for Lambda
resource "aws_iam_role_policy" "lambda_policy" {
  name = "nsw-distillery-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.distillery_data.arn,
          "${aws_s3_bucket.distillery_data.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.distillery_notifications.arn
      }
    ]
  })
}

# Lambda function
resource "aws_lambda_function" "monthly_workflow" {
  filename         = "lambda_deployment.zip"
  function_name    = "nsw-distillery-monthly-workflow"
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_monthly_workflow.lambda_handler"
  runtime         = "python3.11"
  timeout         = 900  # 15 minutes
  memory_size     = 1024  # 1GB RAM

  environment {
    variables = {
      S3_BUCKET            = aws_s3_bucket.distillery_data.bucket
      SNS_TOPIC_ARN        = aws_sns_topic.distillery_notifications.arn
      GOOGLE_PLACES_API    = var.google_places_api_key
      MAX_CONTACT_LOOKUPS  = "100"  # Adjust based on budget
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda_policy,
    aws_cloudwatch_log_group.lambda_logs,
  ]
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/nsw-distillery-monthly-workflow"
  retention_in_days = 30
}

# EventBridge rule to trigger monthly
resource "aws_cloudwatch_event_rule" "monthly_schedule" {
  name                = "nsw-distillery-monthly-trigger"
  description         = "Trigger monthly NSW distillery search"
  schedule_expression = "cron(0 9 5 * ? *)"  # 9 AM on 5th of every month
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.monthly_schedule.name
  target_id = "LambdaTarget"
  arn       = aws_lambda_function.monthly_workflow.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.monthly_workflow.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.monthly_schedule.arn
}

# Outputs
output "s3_bucket_name" {
  description = "Name of the S3 bucket for data storage"
  value       = aws_s3_bucket.distillery_data.bucket
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.monthly_workflow.function_name
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for notifications"
  value       = aws_sns_topic.distillery_notifications.arn
}
