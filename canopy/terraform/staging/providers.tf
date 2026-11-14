provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "rewildingCities"
      Environment = var.environment_name
      ManagedBy   = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}
