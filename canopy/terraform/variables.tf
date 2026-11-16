variable "aws_region" {
  description = "Region for every regional resource"
  type        = string
  default     = "us-east-1"
}

variable "environment_name" {
  description = "Environment tag and name component; the canonical bucket is production"
  type        = string
  default     = "production"
}

variable "create_budget" {
  description = "Whether this stack makes the account's monthly budget. False where the account already has one (Kalli's account keeps its console budget); the library's handover sets true"
  type        = bool
  default     = true
}

variable "budget_name" {
  description = "Name of the account-wide monthly cost budget"
  type        = string
  default     = "rewilding-monthly"
}

variable "monthly_budget_limit_usd" {
  description = "Monthly cost budget, excluding credits and refunds"
  type        = number
  default     = 50
}

variable "budget_alert_email_addresses" {
  description = "Addresses that receive budget alerts; the budget refuses to plan without one. Set through TF_VAR_budget_alert_email_addresses, never a committed file"
  type        = list(string)
  default     = []
}

variable "access_log_retention_days" {
  description = "How long bucket access logs are kept in CloudWatch Logs"
  type        = number
  default     = 90
}

variable "cloudfront_price_class" {
  description = "CloudFront edge coverage; PriceClass_100 is North America and Europe, the cheapest"
  type        = string
  default     = "PriceClass_100"
}
