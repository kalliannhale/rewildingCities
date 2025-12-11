# terraform/outputs.tf
# Values you'll need after terraform apply

output "ecr_repository_url" {
  description = "URL for pushing Docker images"
  value       = aws_ecr_repository.main.repository_url
}

output "s3_bucket_name" {
  description = "S3 bucket for data and outputs"
  value       = aws_s3_bucket.main.id
}

output "batch_job_queue" {
  description = "Job queue ARN for submitting jobs"
  value       = aws_batch_job_queue.main.arn
}

output "batch_job_definition" {
  description = "Job definition ARN for running experiments"
  value       = aws_batch_job_definition.experiment.arn
}

output "aws_region" {
  description = "AWS region (for CLI commands)"
  value       = var.aws_region
}

# Helpful command outputs
output "docker_login_command" {
  description = "Run this to authenticate Docker with ECR"
  value       = "aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.main.repository_url}"
}

output "docker_push_commands" {
  description = "Run these to push your image"
  value       = <<-EOT
    docker tag rewilding-cities:latest ${aws_ecr_repository.main.repository_url}:latest
    docker push ${aws_ecr_repository.main.repository_url}:latest
  EOT
}

output "submit_job_command" {
  description = "Run this to submit a job"
  value       = <<-EOT
    aws batch submit-job \
      --job-name test-experiment \
      --job-queue ${aws_batch_job_queue.main.name} \
      --job-definition ${aws_batch_job_definition.experiment.name}
  EOT
}
