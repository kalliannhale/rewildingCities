resource "aws_s3_bucket" "soil" {
  bucket        = local.bucket_name
  force_destroy = true
  
  tags = merge(local.common_tags, {
    Component = "soil"
  })
}

resource "aws_s3_bucket_notification" "trigger" {
  bucket = aws_s3_bucket.soil.id
  
  queue {
    queue_arn = aws_sqs_queue.main.arn
    events    = ["s3:ObjectCreated:*"]
  }
  
  depends_on = [aws_sqs_queue_policy.s3_to_sqs]
}
