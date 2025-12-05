resource "aws_cloudwatch_metric_alarm" "dlq_alarm" {
  alarm_name          = "rewilding-dlq-alarm"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Triggered when messages appear in the Dead Letter Queue"
  
  dimensions = {
    QueueName = aws_sqs_queue.dlq.name
  }
  
  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
  
  tags = merge(local.common_tags, {
    Component = "monitoring"
  })
}
