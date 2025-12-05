variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (localstack or aws)"
  type        = string
  default     = "localstack"
  
  validation {
    condition     = contains(["localstack", "aws"], var.environment)
    error_message = "Environment must be 'localstack' or 'aws'."
  }
}

variable "account_id" {
  description = "AWS Account ID (required for aws environment)"
  type        = string
  default     = "000000000000"
}

variable "alert_email" {
  description = "Email address for DLQ alerts"
  type        = string
  default     = "alerts@example.com"
}

locals {
  bucket_name = var.environment == "localstack" ? "rewilding-soil" : "rewilding-soil-${var.account_id}"
  lambda_role = var.environment == "localstack" ? "arn:aws:iam::000000000000:role/lambda-role" : "arn:aws:iam::${var.account_id}:role/LabRole"
  
  common_tags = {
    Project     = "rewildingCities"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
