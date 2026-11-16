locals {
  budget_actual_alert_thresholds_percent = [25, 50, 80, 100]
}

# Made only where create_budget is true. Where it is true, apply this first,
# before any other resource (Contract 2, section 5).
resource "aws_budgets_budget" "monthly" {
  count = var.create_budget ? 1 : 0

  name         = var.budget_name
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_limit_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  # Credits would offset spend and keep every alert silent.
  cost_types {
    include_credit = false
    include_refund = false
  }

  dynamic "notification" {
    for_each = local.budget_actual_alert_thresholds_percent
    content {
      notification_type          = "ACTUAL"
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "PERCENTAGE"
      subscriber_email_addresses = var.budget_alert_email_addresses
    }
  }

  notification {
    notification_type          = "FORECASTED"
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    subscriber_email_addresses = var.budget_alert_email_addresses
  }

  lifecycle {
    precondition {
      condition     = length(var.budget_alert_email_addresses) > 0
      error_message = "The budget needs at least one alert address: set TF_VAR_budget_alert_email_addresses, or set create_budget to false."
    }
  }
}
