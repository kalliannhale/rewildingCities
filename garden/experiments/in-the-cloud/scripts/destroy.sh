#!/bin/bash
set -e
ENVIRONMENT="${1:-localstack}"
cd "$(dirname "$0")/../terraform"
if [ "$ENVIRONMENT" == "localstack" ]; then
    terraform destroy -var-file="localstack.tfvars" -auto-approve
else
    terraform destroy -var-file="aws.tfvars" -auto-approve
fi
