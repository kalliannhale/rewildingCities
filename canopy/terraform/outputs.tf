output "canonical_bucket_name" {
  value = aws_s3_bucket.canonical.id
}

output "canonical_bucket_arn" {
  value = aws_s3_bucket.canonical.arn
}

output "cloudfront_domain_name" {
  description = "Public reads go to https://<this>/harvests/..."
  value       = aws_cloudfront_distribution.canonical.domain_name
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.canonical.id
}

output "canonical_writer_role_arn" {
  description = "The role_arn for the rewilding-writer AWS profile"
  value       = aws_iam_role.canonical_writer.arn
}

output "access_log_group_name" {
  value = aws_cloudwatch_log_group.canonical_bucket_access.name
}

output "budget_name" {
  description = "Null where create_budget is false"
  value       = one(aws_budgets_budget.monthly[*].name)
}
