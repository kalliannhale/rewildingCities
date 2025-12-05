#!/bin/bash
set -e
cd "$(dirname "$0")/../lambda"
rm -rf package
mkdir -p package
pip install pyyaml -t package/ --quiet
cp validator.py package/
