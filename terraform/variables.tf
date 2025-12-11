# terraform/variables.tf
# Configurable values for rewildingCities infrastructure

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used as prefix for all resources"
  type        = string
  default     = "rewilding-cities"
}

variable "environment" {
  description = "Environment tag (demo, dev, prod)"
  type        = string
  default     = "demo"
}

# Tags applied to all resources
variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project   = "rewildingCities"
    ManagedBy = "terraform"
  }
}
