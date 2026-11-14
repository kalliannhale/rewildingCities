output "staging_bucket_name" {
  value = aws_s3_bucket.staging.id
}

output "staging_bucket_arn" {
  value = aws_s3_bucket.staging.arn
}

output "access_log_group_name" {
  value = aws_cloudwatch_log_group.staging_bucket_access.name
}

output "budget_name" {
  value = aws_budgets_budget.monthly.name
}
