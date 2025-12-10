# ═══════════════════════════════════════════════════════════════════════════════
# terraform/storage.tf
# S3 buckets for city data caches
# ═══════════════════════════════════════════════════════════════════════════════

variable "cities" {
  description = "List of city IDs with active plots"
  type        = list(string)
  default     = ["nyc"]
}

# One bucket per city
resource "aws_s3_bucket" "city_cache" {
  for_each = toset(var.cities)
  
  bucket = "rewilding-${each.key}-cache"
  
  tags = {
    Project = "rewildingCities"
    City    = each.key
  }
}

# Block public access (data stays private)
resource "aws_s3_bucket_public_access_block" "city_cache" {
  for_each = toset(var.cities)
  
  bucket = aws_s3_bucket.city_cache[each.key].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle rule: clean up old logs after 30 days
resource "aws_s3_bucket_lifecycle_configuration" "city_cache" {
  for_each = toset(var.cities)
  
  bucket = aws_s3_bucket.city_cache[each.key].id

  rule {
    id     = "cleanup-logs"
    status = "Enabled"
    
    filter {
      prefix = "logs/"
    }
    
    expiration {
      days = 30
    }
  }
}
