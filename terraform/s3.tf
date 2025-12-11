# terraform/s3.tf
# Storage for data, envelopes, and harvest outputs

resource "aws_s3_bucket" "main" {
  bucket = "${var.project_name}-${var.environment}"

  # For demo, allow destruction even with objects inside
  force_destroy = true
}

# Block all public access (our data stays private)
resource "aws_s3_bucket_public_access_block" "main" {
  bucket = aws_s3_bucket.main.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Versioning off for demo (saves storage costs)
resource "aws_s3_bucket_versioning" "main" {
  bucket = aws_s3_bucket.main.id

  versioning_configuration {
    status = "Disabled"
  }
}

# Create the folder structure we expect
# (S3 doesn't really have folders, but this creates the "prefixes")
resource "aws_s3_object" "plots_nyc_data" {
  bucket  = aws_s3_bucket.main.id
  key     = "plots/nyc/.data/.gitkeep"
  content = "# Data files live here"
}

resource "aws_s3_object" "plots_nyc_envelopes" {
  bucket  = aws_s3_bucket.main.id
  key     = "plots/nyc/.envelopes/.gitkeep"
  content = "# Envelope outputs live here"
}

resource "aws_s3_object" "harvest" {
  bucket  = aws_s3_bucket.main.id
  key     = "harvest/.gitkeep"
  content = "# Harvest outputs live here"
}

resource "aws_s3_object" "compost_logs" {
  bucket  = aws_s3_bucket.main.id
  key     = "compost/logs/.gitkeep"
  content = "# Run logs live here"
}
