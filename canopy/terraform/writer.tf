# The canonical write's identity (D-308): a role, assumed from a person's own
# login through an AWS profile, so no access key exists for it. It may write
# and read under harvests/ and never delete. The bucket policy's conditional
# write rules bind it as they bind everyone (D-309).

data "aws_iam_policy_document" "writer_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${local.account_id}:root"]
    }
  }
}

resource "aws_iam_role" "canonical_writer" {
  name                 = "rewilding-canonical-writer"
  path                 = "/rewilding/"
  description          = "Writes canonical harvests under harvests/; never deletes"
  assume_role_policy   = data.aws_iam_policy_document.writer_trust.json
  max_session_duration = 3600
}

data "aws_iam_policy_document" "writer" {
  # Without list, a missing object reads as forbidden rather than missing.
  statement {
    sid       = "ListTheBucket"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.canonical.arn]
  }

  # If-Match needs get as well as put.
  statement {
    sid    = "WriteAndReadHarvests"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
    ]
    resources = ["${aws_s3_bucket.canonical.arn}/harvests/*"]
  }

  statement {
    sid    = "NeverDelete"
    effect = "Deny"
    actions = [
      "s3:DeleteObject",
      "s3:DeleteObjectVersion",
    ]
    resources = ["${aws_s3_bucket.canonical.arn}/*"]
  }
}

resource "aws_iam_role_policy" "canonical_writer" {
  name   = "canonical-write"
  role   = aws_iam_role.canonical_writer.id
  policy = data.aws_iam_policy_document.writer.json
}
