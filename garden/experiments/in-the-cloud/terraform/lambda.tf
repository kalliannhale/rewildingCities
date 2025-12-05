data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/package"
  output_path = "${path.module}/../lambda/validator.zip"
}

resource "aws_lambda_function" "validator" {
  function_name    = "rewilding-validator"
  role             = local.lambda_role
  handler          = "validator.lambda_handler"
  runtime          = "python3.9"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 30
  memory_size      = 128
  
  environment {
    variables = {
      ENVIRONMENT = var.environment
    }
  }
  
  tags = merge(local.common_tags, {
    Component = "validator"
  })
}

resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.main.arn
  function_name    = aws_lambda_function.validator.arn
  batch_size       = 1
  enabled          = true
}

resource "aws_lambda_permission" "sqs" {
  statement_id  = "AllowSQSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.validator.function_name
  principal     = "sqs.amazonaws.com"
  source_arn    = aws_sqs_queue.main.arn
}
