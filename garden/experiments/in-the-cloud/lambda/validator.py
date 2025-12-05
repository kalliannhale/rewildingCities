"""
🌱 validator.py
The gatekeeper at the garden entrance.
Every file that lands in S3 must pass through her.

Pipeline: S3 → SQS → Lambda (this) → sidecar registration
If poisoned: → DLQ → SNS alert
"""

import json
import yaml
import boto3
import os
from datetime import datetime, timezone


# ------------------------------------
# 🌿 CONFIGURATION
# ------------------------------------

LOCALSTACK_ENDPOINT = os.environ.get("LOCALSTACK_ENDPOINT", None)


def get_s3_client():
    """Points to LocalStack if endpoint is set, otherwise AWS."""
    if LOCALSTACK_ENDPOINT:
        return boto3.client("s3", endpoint_url=LOCALSTACK_ENDPOINT)
    return boto3.client("s3")


# ------------------------------------
# 🔍 IDENTIFY: What kind of file are you?
# ------------------------------------

def identify_file_type(key: str) -> str:
    key_lower = key.lower()
    
    if key_lower.endswith((".yml", ".yaml")):
        return "manifest"
    elif key_lower.endswith(".geojson"):
        return "geojson"
    elif key_lower.endswith((".tif", ".tiff")):
        return "geotiff"
    else:
        return "unknown"


# ------------------------------------
# ✅ VALIDATE: Are you who you say you are?
# ------------------------------------

def validate_manifest(content: bytes) -> dict:
    """
    Required:
      - city.name (no untitled communities)
      - city.id (machine-readable)
      - crs.working (spatial analysis needs this)
    
    Optional:
      - datasets (can initialize empty)
    """
    errors = []
    
    # Can we even parse this?
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        return {
            "status": "poisoned",
            "errors": [f"YAML parse error: {str(e)}"]
        }
    
    if not isinstance(data, dict):
        return {
            "status": "poisoned",
            "errors": ["Manifest is not a valid YAML dictionary"]
        }
    
    # Check required fields
    city = data.get("city", {})
    crs = data.get("crs", {})
    
    if not city.get("name"):
        errors.append("Missing required field: city.name")
    
    if not city.get("id"):
        errors.append("Missing required field: city.id")
    
    if not crs.get("working"):
        errors.append("Missing required field: crs.working")
    
    if errors:
        return {"status": "invalid", "errors": errors}
    
    return {"status": "ready", "errors": []}


def validate_geojson(content: bytes) -> dict:
    """Basic GeoJSON structure check."""
    errors = []
    
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return {
            "status": "poisoned",
            "errors": [f"JSON parse error: {str(e)}"]
        }
    
    if not isinstance(data, dict):
        return {
            "status": "poisoned",
            "errors": ["GeoJSON is not a valid JSON object"]
        }
    
    if "type" not in data:
        errors.append("Missing required field: type")
    
    if data.get("type") == "FeatureCollection" and "features" not in data:
        errors.append("FeatureCollection missing 'features' array")
    
    if data.get("type") == "Feature" and "geometry" not in data:
        errors.append("Feature missing 'geometry'")
    
    if errors:
        return {"status": "invalid", "errors": errors}
    
    return {"status": "ready", "errors": []}


def validate_geotiff(content: bytes) -> dict:
    """Check TIFF magic bytes. Light validation."""
    if len(content) < 4:
        return {
            "status": "poisoned",
            "errors": ["File too small to be a valid TIFF"]
        }
    
    magic = content[:4]
    valid_le = magic[:2] == b'II' and magic[2:4] == b'\x2a\x00'
    valid_be = magic[:2] == b'MM' and magic[2:4] == b'\x00\x2a'
    
    if not (valid_le or valid_be):
        return {
            "status": "poisoned",
            "errors": ["Invalid TIFF magic bytes"]
        }
    
    return {"status": "ready", "errors": []}


def validate_unknown(content: bytes) -> dict:
    """Unknown file type. Not corrupt, just unexpected."""
    return {
        "status": "invalid",
        "errors": ["Unknown file type - cannot validate"]
    }


VALIDATORS = {
    "manifest": validate_manifest,
    "geojson": validate_geojson,
    "geotiff": validate_geotiff,
    "unknown": validate_unknown,
}


# ------------------------------------
# 📝 REGISTER: Write the sidecar
# ------------------------------------

def write_sidecar(s3_client, bucket: str, key: str, file_type: str, result: dict):
    """
    manifest.yml → manifest.yml.meta.json
    The file now has paperwork.
    """
    sidecar_key = f"{key}.meta.json"
    
    sidecar_content = {
        "source_file": key,
        "file_type": file_type,
        "status": result["status"],
        "errors": result["errors"],
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "validator_version": "0.1.0"
    }
    
    s3_client.put_object(
        Bucket=bucket,
        Key=sidecar_key,
        Body=json.dumps(sidecar_content, indent=2),
        ContentType="application/json"
    )
    
    return sidecar_key


# ------------------------------------
# 🚪 THE KNOCK: Lambda Handler
# ------------------------------------

def lambda_handler(event, context):
    """
    The gatekeeper awakens.
    SQS says a file landed. We validate. We register. We route.
    """
    s3_client = get_s3_client()
    
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        
        for s3_record in body.get("Records", []):
            bucket = s3_record["s3"]["bucket"]["name"]
            key = s3_record["s3"]["object"]["key"]
            
            print(f"🌱 Processing: s3://{bucket}/{key}")
            
            # Skip sidecars (no infinite loops)
            if key.endswith(".meta.json"):
                print(f"  ↳ Skipping sidecar file")
                continue
            
            # Identify
            file_type = identify_file_type(key)
            print(f"  ↳ Identified as: {file_type}")
            
            # Fetch
            try:
                response = s3_client.get_object(Bucket=bucket, Key=key)
                content = response["Body"].read()
            except Exception as e:
                print(f"  ↳ ERROR: Could not fetch file: {e}")
                raise
            
            # Validate
            validator = VALIDATORS[file_type]
            result = validator(content)
            print(f"  ↳ Status: {result['status']}")
            
            # Register
            sidecar_key = write_sidecar(s3_client, bucket, key, file_type, result)
            print(f"  ↳ Sidecar: {sidecar_key}")
            
            # Route
            if result["status"] == "poisoned":
                error_msg = f"Poisoned: {key} - {result['errors']}"
                print(f"  ↳ ☠️ {error_msg}")
                raise ValueError(error_msg)
            
            print(f"  ↳ ✅ Done")
    
    return {"statusCode": 200, "body": json.dumps({"message": "Complete"})}
