import os

BEDROCK_AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_FALLBACK_ENABLED = os.getenv("BEDROCK_FALLBACK_ENABLED", "true").lower() == "true"

RATE_LIMIT_TRACKING_ENABLED = os.getenv("RATE_LIMIT_TRACKING_ENABLED", "true").lower() == "true"
RATE_LIMIT_TABLE_NAME = os.getenv("RATE_LIMIT_TABLE_NAME", "claude-proxy-rate-limits")
RETRY_THRESHOLD_SECONDS = int(os.getenv("RETRY_THRESHOLD_SECONDS", "30"))
MAX_RETRY_WAIT_SECONDS = int(os.getenv("MAX_RETRY_WAIT_SECONDS", "10"))

USAGE_TRACKING_ENABLED = os.getenv("USAGE_TRACKING_ENABLED", "true").lower() == "true"
USAGE_TABLE_NAME = os.getenv("USAGE_TABLE_NAME", "claude-proxy-usage")
