#!/bin/bash
set -e
cd "$(dirname "$0")/.."
./scripts/package-lambda.sh
cd terraform
terraform init
terraform apply -var-file="aws.tfvars" -auto-approve
terraform output
