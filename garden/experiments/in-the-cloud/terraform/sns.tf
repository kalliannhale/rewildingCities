resource "aws_sns_topic" "alerts" {
  name = "rewilding-alerts"
  
  tags = merge(local.common_tags, {
    Component = "alerts"
  })
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}
