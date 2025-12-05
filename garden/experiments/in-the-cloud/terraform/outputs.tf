output "bucket_name" {
  description = "S3 bucket name"
  value       = aws_s3_bucket.soil.id
}

output "bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.soil.arn
}

output "queue_url" {
  description = "SQS queue URL"
  value       = aws_sqs_queue.main.url
}

output "dlq_url" {
  description = "Dead Letter Queue URL"
  value       = aws_sqs_queue.dlq.url
}

output "lambda_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.validator.arn
}

output "sns_topic_arn" {
  description = "SNS topic ARN"
  value       = aws_sns_topic.alerts.arn
}

output "environment" {
  description = "Deployment environment"
  value       = var.environment
}
