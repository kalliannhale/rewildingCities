# terraform/iam.tf
# Reference existing lab role instead of creating new ones

data "aws_iam_role" "lab_role" {
  name = "LabRole"
}