import boto3
import time
from datetime import datetime
from config import USAGE_TRACKING_ENABLED, USAGE_TABLE_NAME, BEDROCK_AWS_REGION
import logging

logger = logging.getLogger(__name__)

async def track_usage(user_id: str, model: str, input_tokens: int, output_tokens: int, request_type: str):
    """Track usage in DynamoDB with atomic counters"""
    if not USAGE_TRACKING_ENABLED:
        return

    try:
        dynamodb = boto3.resource("dynamodb", region_name=BEDROCK_AWS_REGION)
        table = dynamodb.Table(USAGE_TABLE_NAME)
        current_time = int(time.time())
        now = datetime.utcnow()

        # Daily key: user_id#YYYY-MM-DD
        daily_key = f"{user_id}#{now.strftime('%Y-%m-%d')}"

        # TTL: 90 days from now
        ttl = current_time + (90 * 24 * 3600)
        iso_timestamp = now.strftime("%Y-%m-%dT%H:%M:%S")

        # Update daily aggregate using atomic counters with safe initialization
        table.update_item(
            Key={
                "user_period": daily_key,
            },
            UpdateExpression=(
                "SET "
                "input_tokens = if_not_exists(input_tokens, :zero) + :input, "
                "output_tokens = if_not_exists(output_tokens, :zero) + :output, "
                "total_tokens = if_not_exists(total_tokens, :zero) + :total, "
                "request_count = if_not_exists(request_count, :zero) + :one, "
                "last_updated_at = :timestamp, "
                "#ttl = :ttl, "
                "period_type = :period_type, "
                "#model = :model, "
                "user_id = :user_id, "
                "request_type = :request_type"
            ),
            ExpressionAttributeNames={
                "#ttl": "ttl",
                "#model": "model",
            },
            ExpressionAttributeValues={
                ":input": input_tokens,
                ":output": output_tokens,
                ":total": input_tokens + output_tokens,
                ":one": 1,
                ":zero": 0,
                ":timestamp": iso_timestamp,
                ":ttl": ttl,
                ":period_type": "daily",
                ":model": model,
                ":user_id": user_id,
                ":request_type": request_type,
            },
        )

        logger.info(f"📊 [USAGE] {user_id}: {input_tokens}+{output_tokens} tokens ({model}, {request_type})")
    except Exception as e:
        logger.error(f"❌ [USAGE ERROR] Failed to store token usage: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")
