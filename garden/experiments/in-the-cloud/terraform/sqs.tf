resource "aws_sqs_queue" "dlq" {
  name                      = "rewilding-dlq"
  message_retention_seconds = 1209600
  
  tags = merge(local.common_tags, {
    Component = "dlq"
  })
}

resource "aws_sqs_queue" "main" {
  name                       = "rewilding-queue"
  visibility_timeout_seconds = 60
  
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
  
  tags = merge(local.common_tags, {
    Component = "queue"
  })
}

resource "aws_sqs_queue_policy" "s3_to_sqs" {
  queue_url = aws_sqs_queue.main.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "s3.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.main.arn
      Condition = {
        ArnLike = {
          "aws:SourceArn" = aws_s3_bucket.soil.arn
        }
      }
    }]
  })
}
