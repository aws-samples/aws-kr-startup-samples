from fastapi import APIRouter, Request
import logging
from config import USAGE_TABLE_NAME

logger = logging.getLogger(__name__)
router = APIRouter()


def get_dynamodb_resource():
    import boto3
    from config import BEDROCK_AWS_REGION

    try:
        return boto3.resource("dynamodb", region_name=BEDROCK_AWS_REGION)
    except Exception as e:
        logger.error(f"Failed to initialize DynamoDB resource: {e}")
        return None


@router.get("/v1/usage/me")
async def get_my_usage(
    raw_request: Request,
    days: int = None,
    date: str = None,
    request_type: str = None,
):
    """
    현재 유저의 토큰 사용량 조회 (쿼리 파라미터에서 user_id 자동 추출)
    """
    user_id = raw_request.query_params.get("claude-code-user", "default")
    return await get_user_usage(
        user_id=user_id, days=days, date=date, request_type=request_type
    )


async def get_user_usage(
    user_id: str,
    days: int = None,
    date: str = None,
    request_type: str = None,
):
    try:
        from datetime import datetime, timedelta
        from boto3.dynamodb.conditions import Key

        dynamodb = get_dynamodb_resource()
        if not dynamodb:
            return {"error": "DynamoDB not available"}

        table = dynamodb.Table(USAGE_TABLE_NAME)

        if date is None and days is None:
            days = 7

        if date:
            start_date = date
            end_date = date
        else:
            start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
            end_date = datetime.utcnow().strftime("%Y-%m-%d")

        if date:
            response = table.query(
                KeyConditionExpression=Key("user_id").eq(user_id)
                & Key("timestamp").between(start_date, start_date + "T99:99:99")
            )
        else:
            response = table.query(
                KeyConditionExpression=Key("user_id").eq(user_id)
                & Key("timestamp").gte(start_date)
            )

        items = response.get("Items", [])

        if request_type:
            items = [item for item in items if item.get("request_type") == request_type]

        total_input = sum(item.get("input_tokens", 0) for item in items)
        total_output = sum(item.get("output_tokens", 0) for item in items)
        total_requests = len(items)

        daily_stats = {}
        for item in items:
            day = item["timestamp"][:10]
            if day not in daily_stats:
                daily_stats[day] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "requests": 0,
                }
            daily_stats[day]["input_tokens"] += item.get("input_tokens", 0)
            daily_stats[day]["output_tokens"] += item.get("output_tokens", 0)
            daily_stats[day]["requests"] += 1

        result = {
            "user_id": user_id,
            "request_type": request_type or "all",
            "summary": {
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "total_tokens": total_input + total_output,
                "total_requests": total_requests,
            },
            "daily_stats": daily_stats,
        }

        if date:
            result["date"] = date
        else:
            result["period_days"] = days

        return result

    except Exception as e:
        logger.error(f"Error fetching usage for user {user_id}: {e}")
        return {"error": str(e)}


@router.get("/v1/usage")
async def get_all_users_usage(
    days: int = None,
    date: str = None,
    request_type: str = "bedrock",
):
    try:
        from datetime import datetime, timedelta
        from boto3.dynamodb.conditions import Attr

        dynamodb = get_dynamodb_resource()
        if not dynamodb:
            return {"error": "DynamoDB not available"}

        table = dynamodb.Table(USAGE_TABLE_NAME)

        if date is None and days is None:
            days = 7

        if date:
            start_timestamp = date
            end_timestamp = date + "T99:99:99"
        else:
            start_timestamp = (datetime.utcnow() - timedelta(days=days)).strftime(
                "%Y-%m-%dT%H:%M:%S"
            )
            end_timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

        if date:
            if request_type == "all":
                response = table.scan(
                    FilterExpression=Attr("timestamp").between(
                        start_timestamp, end_timestamp
                    )
                )
            else:
                response = table.scan(
                    FilterExpression=Attr("timestamp").between(
                        start_timestamp, end_timestamp
                    )
                    & Attr("request_type").eq(request_type)
                )
        else:
            if request_type == "all":
                response = table.scan(
                    FilterExpression=Attr("timestamp").gte(start_timestamp)
                )
            else:
                response = table.scan(
                    FilterExpression=Attr("timestamp").gte(start_timestamp)
                    & Attr("request_type").eq(request_type)
                )

        items = response.get("Items", [])

        user_stats = {}
        for item in items:
            uid = item.get("user_id")
            if uid not in user_stats:
                user_stats[uid] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "requests": 0,
                }
            user_stats[uid]["input_tokens"] += item.get("input_tokens", 0)
            user_stats[uid]["output_tokens"] += item.get("output_tokens", 0)
            user_stats[uid]["requests"] += 1

        total_users = len(user_stats)
        total_input = sum(s["input_tokens"] for s in user_stats.values())
        total_output = sum(s["output_tokens"] for s in user_stats.values())
        total_requests = sum(s["requests"] for s in user_stats.values())

        result = {
            "request_type": request_type,
            "summary": {
                "total_users": total_users,
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "total_tokens": total_input + total_output,
                "total_requests": total_requests,
            },
            "users": user_stats,
        }

        if date:
            result["date"] = date
        else:
            result["period_days"] = days

        return result

    except Exception as e:
        logger.error(f"Error fetching all users usage: {e}")
        return {"error": str(e)}
