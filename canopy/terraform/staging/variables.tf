variable "aws_region" {
  description = "Region for every regional resource; a new-experience project can only build in its assigned Region"
  type        = string
  default     = "us-east-2"
}

variable "environment_name" {
  description = "Environment tag and name component, e.g. staging or production"
  type        = string
  default     = "staging"
}

variable "budget_name" {
  description = "Name of the account-wide monthly cost budget"
  type        = string
  default     = "rewilding-testing-monthly"
}

variable "monthly_budget_limit_usd" {
  description = "Monthly cost budget, excluding credits and refunds"
  type        = number
  default     = 50
}

variable "budget_alert_email_addresses" {
  description = "Addresses that receive budget alerts"
  type        = list(string)
}

variable "access_log_retention_days" {
  description = "How long bucket access logs are kept in CloudWatch Logs"
  type        = number
  default     = 90
}

variable "noncurrent_object_version_retention_days" {
  description = "How long replaced snapshot versions stay restorable before S3 deletes them"
  type        = number
  default     = 90
}
