# The public reaches canonical files only through CloudFront (D-302). The bucket
# stays private; the bucket policy lets this distribution read harvests/ alone.

data "aws_cloudfront_cache_policy" "optimized" {
  name = "Managed-CachingOptimized"
}

data "aws_cloudfront_cache_policy" "disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_origin_request_policy" "cors_s3" {
  name = "Managed-CORS-S3Origin"
}

resource "aws_cloudfront_origin_access_control" "canonical" {
  name                              = "rewilding-${var.environment_name}-canonical"
  description                       = "CloudFront signs every read of the canonical bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# Any origin may read; reads only (D-310). The range headers are exposed so
# DuckDB can read GeoParquet by byte range.
resource "aws_cloudfront_response_headers_policy" "cors" {
  name = "rewilding-${var.environment_name}-cors"

  cors_config {
    access_control_allow_credentials = false
    access_control_max_age_sec       = 86400
    origin_override                  = true

    access_control_allow_headers {
      items = ["*"]
    }

    access_control_allow_methods {
      items = ["GET", "HEAD", "OPTIONS"]
    }

    access_control_allow_origins {
      items = ["*"]
    }

    access_control_expose_headers {
      items = ["ETag", "Content-Length", "Content-Range", "Accept-Ranges"]
    }
  }
}

resource "aws_cloudfront_distribution" "canonical" {
  enabled         = true
  is_ipv6_enabled = true
  http_version    = "http2and3"
  comment         = "rewildingCities canonical harvests (${var.environment_name})"
  price_class     = var.cloudfront_price_class

  origin {
    origin_id                = "canonical"
    domain_name              = aws_s3_bucket.canonical.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.canonical.id
  }

  # Versions never change, so they cache as long as CloudFront allows.
  default_cache_behavior {
    target_origin_id           = "canonical"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.optimized.id
    origin_request_policy_id   = data.aws_cloudfront_origin_request_policy.cors_s3.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.cors.id
  }

  # A pointer moves, so it is never cached.
  ordered_cache_behavior {
    path_pattern               = "harvests/*/current"
    target_origin_id           = "canonical"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.disabled.id
    origin_request_policy_id   = data.aws_cloudfront_origin_request_policy.cors_s3.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.cors.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}
