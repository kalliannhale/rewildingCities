locals {
  access_log_group_name = "/aws/vendedlogs/s3/${local.staging_bucket_name}/S3_SERVER_ACCESS_LOGS"
  access_log_group_arn  = "arn:aws:logs:${var.aws_region}:${local.account_id}:log-group:${local.access_log_group_name}"
}

data "aws_iam_policy_document" "access_log_key" {
  statement {
    sid       = "AllowAccountAdministration"
    effect    = "Allow"
    actions   = ["kms:*"]
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${local.account_id}:root"]
    }
  }

  statement {
    sid    = "AllowCloudWatchLogsForThisLogGroupOnly"
    effect = "Allow"
    actions = [
      "kms:Encrypt*",
      "kms:Decrypt*",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:Describe*",
    ]
    resources = ["*"]

    principals {
      type        = "Service"
      identifiers = ["logs.${var.aws_region}.amazonaws.com"]
    }

    condition {
      test     = "ArnEquals"
      variable = "kms:EncryptionContext:aws:logs:arn"
      values   = [local.access_log_group_arn]
    }
  }
}

resource "aws_kms_key" "access_logs" {
  description             = "Encrypts S3 access logs for the ${var.environment_name} bucket"
  enable_key_rotation     = true
  deletion_window_in_days = 7
  policy                  = data.aws_iam_policy_document.access_log_key.json
}

resource "aws_kms_alias" "access_logs" {
  name          = "alias/rewilding-cities-${var.environment_name}-access-logs"
  target_key_id = aws_kms_key.access_logs.key_id
}

resource "aws_cloudwatch_log_group" "staging_bucket_access" {
  name              = local.access_log_group_name
  retention_in_days = var.access_log_retention_days
  kms_key_id        = aws_kms_key.access_logs.arn
}

resource "aws_cloudwatch_log_delivery_source" "staging_bucket_access" {
  name         = "rewilding-${var.environment_name}-bucket-access"
  log_type     = "S3_SERVER_ACCESS_LOGS"
  resource_arn = aws_s3_bucket.staging.arn
}

resource "aws_cloudwatch_log_delivery_destination" "staging_bucket_access" {
  name = "rewilding-${var.environment_name}-bucket-access-logs"

  delivery_destination_configuration {
    destination_resource_arn = aws_cloudwatch_log_group.staging_bucket_access.arn
  }
}

resource "aws_cloudwatch_log_delivery" "staging_bucket_access" {
  delivery_source_name     = aws_cloudwatch_log_delivery_source.staging_bucket_access.name
  delivery_destination_arn = aws_cloudwatch_log_delivery_destination.staging_bucket_access.arn
}
