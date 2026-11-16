locals {
  account_id = data.aws_caller_identity.current.account_id

  # Account-regional namespace names must end in -<account id>-<region>-an.
  canonical_bucket_name = "rewilding-cities-${var.environment_name}-${local.account_id}-${var.aws_region}-an"
}

resource "aws_s3_bucket" "canonical" {
  bucket           = local.canonical_bucket_name
  bucket_namespace = "account-regional"
  force_destroy    = false
}

resource "aws_s3_bucket_public_access_block" "canonical" {
  bucket = aws_s3_bucket.canonical.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "canonical" {
  bucket = aws_s3_bucket.canonical.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "canonical" {
  bucket = aws_s3_bucket.canonical.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "canonical" {
  bucket = aws_s3_bucket.canonical.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled       = true
    blocked_encryption_types = ["SSE-C"]
  }
}

resource "aws_s3_bucket_abac" "canonical" {
  bucket = aws_s3_bucket.canonical.id

  abac_status {
    status = "Enabled"
  }
}

# Noncurrent versions are kept (D-307): only a current pointer is ever
# overwritten, so expiring them would erase the history of pointer moves.
resource "aws_s3_bucket_lifecycle_configuration" "canonical" {
  bucket = aws_s3_bucket.canonical.id

  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.canonical]
}

# Preflight requests reach S3 through CloudFront; S3 answers them here (D-310).
resource "aws_s3_bucket_cors_configuration" "canonical" {
  bucket = aws_s3_bucket.canonical.id

  cors_rule {
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    allowed_headers = ["*"]
    expose_headers  = ["ETag", "Content-Length", "Content-Range", "Accept-Ranges"]
    max_age_seconds = 86400
  }
}

data "aws_iam_policy_document" "canonical_bucket" {
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.canonical.arn,
      "${aws_s3_bucket.canonical.arn}/*",
    ]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  statement {
    sid       = "AllowCloudFrontReadHarvestsOnly"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.canonical.arn}/harvests/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.canonical.arn]
    }
  }

  # A version is written once and never replaced (D-309).
  statement {
    sid       = "DenyVersionWriteWithoutIfNoneMatch"
    effect    = "Deny"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.canonical.arn}/harvests/*/versions/*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Null"
      variable = "s3:if-none-match"
      values   = ["true"]
    }

    condition {
      test     = "Bool"
      variable = "s3:ObjectCreationOperation"
      values   = ["true"]
    }
  }

  # A pointer is created with If-None-Match and moved with If-Match (D-309).
  statement {
    sid       = "DenyPointerWriteWithoutCondition"
    effect    = "Deny"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.canonical.arn}/harvests/*/current"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Null"
      variable = "s3:if-none-match"
      values   = ["true"]
    }

    condition {
      test     = "Null"
      variable = "s3:if-match"
      values   = ["true"]
    }

    condition {
      test     = "Bool"
      variable = "s3:ObjectCreationOperation"
      values   = ["true"]
    }
  }
}

resource "aws_s3_bucket_policy" "canonical" {
  bucket = aws_s3_bucket.canonical.id
  policy = data.aws_iam_policy_document.canonical_bucket.json

  depends_on = [aws_s3_bucket_public_access_block.canonical]
}
