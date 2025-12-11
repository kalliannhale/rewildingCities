# terraform/batch.tf
# AWS Batch compute environment, job queue, and job definition

# ============================================
# Compute Environment (Fargate = serverless, no EC2 management)
# ============================================
resource "aws_batch_compute_environment" "main" {
  compute_environment_name = "${var.project_name}-compute"
  type                     = "MANAGED"
  state                    = "ENABLED"

  compute_resources {
    type      = "FARGATE"
    max_vcpus = 4

    subnets            = data.aws_subnets.default.ids
    security_group_ids = [aws_security_group.batch.id]
  }

  # Use existing LabRole
  service_role = data.aws_iam_role.lab_role.arn

  depends_on = [aws_security_group.batch]
}

# ============================================
# Job Queue
# ============================================
resource "aws_batch_job_queue" "main" {
  name     = "${var.project_name}-queue"
  state    = "ENABLED"
  priority = 1

  compute_environment_order {
    order               = 1
    compute_environment = aws_batch_compute_environment.main.arn
  }
}

# ============================================
# Job Definition
# ============================================
resource "aws_batch_job_definition" "experiment" {
  name = "${var.project_name}-experiment"
  type = "container"

  platform_capabilities = ["FARGATE"]

  container_properties = jsonencode({
    image = "${aws_ecr_repository.main.repository_url}:latest"

    resourceRequirements = [
      { type = "VCPU", value = "1" },
      { type = "MEMORY", value = "2048" }
    ]

    # Use existing LabRole for both
    executionRoleArn = data.aws_iam_role.lab_role.arn
    jobRoleArn       = data.aws_iam_role.lab_role.arn

    command = ["python", "experiment.py"]

    environment = [
      { name = "REWILDING_ENV", value = var.environment },
      { name = "REWILDING_BUCKET", value = aws_s3_bucket.main.id }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/aws/batch/${var.project_name}"
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "experiment"
      }
    }

    networkConfiguration = {
      assignPublicIp = "ENABLED"
    }

    fargatePlatformConfiguration = {
      platformVersion = "LATEST"
    }
  })

  retry_strategy {
    attempts = 1
  }

  timeout {
    attempt_duration_seconds = 900
  }
}

# ============================================
# Supporting resources (networking)
# ============================================
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_security_group" "batch" {
  name        = "${var.project_name}-batch-sg"
  description = "Security group for Batch compute"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_cloudwatch_log_group" "batch" {
  name              = "/aws/batch/${var.project_name}"
  retention_in_days = 7
}