terraform {
  required_version = ">= 1.0.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  skip_credentials_validation = var.environment == "localstack"
  skip_metadata_api_check     = var.environment == "localstack"
  skip_requesting_account_id  = var.environment == "localstack"
  
  dynamic "endpoints" {
    for_each = var.environment == "localstack" ? [1] : []
    content {
      s3         = "http://localhost:4566"
      sqs        = "http://localhost:4566"
      lambda     = "http://localhost:4566"
      sns        = "http://localhost:4566"
      iam        = "http://localhost:4566"
      cloudwatch = "http://localhost:4566"
      sts        = "http://localhost:4566"
    }
  }
}
