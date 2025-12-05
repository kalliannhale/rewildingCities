#!/bin/bash
set -e
ENVIRONMENT="${1:-localstack}"
if [ "$ENVIRONMENT" == "localstack" ]; then
    AWS_CMD="awslocal"
    BUCKET="rewilding-soil"
else
    AWS_CMD="aws"
    BUCKET="rewilding-soil-730335660321"
fi
mkdir -p test-files
echo 'city:
  name: "Atlanta"
  id: "atl"
crs:
  working: "EPSG:4326"' > test-files/valid-manifest.yml
echo 'city:
  id: "atl"
crs:
  working: "EPSG:4326"' > test-files/invalid-manifest.yml
echo 'city:
  name: [[[broken yaml
  this is not valid' > test-files/poison.yml
echo "Testing valid manifest..."
$AWS_CMD s3 cp test-files/valid-manifest.yml "s3://$BUCKET/valid-manifest.yml"
sleep 3
$AWS_CMD s3 cp "s3://$BUCKET/valid-manifest.yml.meta.json" -
echo "Testing invalid manifest..."
$AWS_CMD s3 cp test-files/invalid-manifest.yml "s3://$BUCKET/invalid-manifest.yml"
sleep 3
$AWS_CMD s3 cp "s3://$BUCKET/invalid-manifest.yml.meta.json" -
echo "Testing poison pill..."
$AWS_CMD s3 cp test-files/poison.yml "s3://$BUCKET/poison.yml"
sleep 3
$AWS_CMD s3 cp "s3://$BUCKET/poison.yml.meta.json" -
