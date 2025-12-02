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

        # Generate list of dates to query
        if date:
            dates = [date]
        else:
            dates = [
                (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(days)
            ]

        # Query daily aggregates for each date
        daily_stats = {}
        total_input = 0
        total_output = 0
        total_requests = 0

        for query_date in dates:
            user_period_key = f"{user_id}#{query_date}"

            # Get item for this date (no Sort Key)
            try:
                response = table.get_item(Key={"user_period": user_period_key})
                item = response.get("Item")
                
                if item:
                    # Check request_type filter if specified
                    if request_type and item.get("request_type") != request_type:
                        continue
                    
                    day_input = item.get("input_tokens", 0)
                    day_output = item.get("output_tokens", 0)
                    day_requests = item.get("request_count", 0)
                else:
                    day_input = 0
                    day_output = 0
                    day_requests = 0
            except Exception as e:
                logger.warning(f"Error getting item for {user_period_key}: {e}")
                day_input = 0
                day_output = 0
                day_requests = 0

            if day_input > 0 or day_output > 0 or day_requests > 0:
                daily_stats[query_date] = {
                    "input_tokens": day_input,
                    "output_tokens": day_output,
                    "total_tokens": day_input + day_output,
                    "requests": day_requests,
                }

                total_input += day_input
                total_output += day_output
                total_requests += day_requests

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
        return {"error": "An internal error has occurred."}


@router.get("/v1/usage")
async def get_all_users_usage(
    days: int = None,
    date: str = None,
    request_type: str = "bedrock",
):
    try:
        from datetime import datetime, timedelta
        from boto3.dynamodb.conditions import Key, Attr

        dynamodb = get_dynamodb_resource()
        if not dynamodb:
            return {"error": "DynamoDB not available"}

        table = dynamodb.Table(USAGE_TABLE_NAME)

        if date is None and days is None:
            days = 7

        # Generate list of dates to query
        if date:
            dates = [date]
        else:
            dates = [
                (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(days)
            ]

        user_stats = {}

        # Scan all items and filter by date range (no GSI)
        response = table.scan(FilterExpression=Attr("period_type").eq("daily"))
        items = response.get("Items", [])

        # Continue scanning if there are more items
        while "LastEvaluatedKey" in response:
            response = table.scan(
                FilterExpression=Attr("period_type").eq("daily"),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))

        # Filter items by date range and request_type in memory
        filtered_items = []
        for item in items:
            user_period = item.get("user_period", "")
            # Extract date from user_period (format: "user_id#YYYY-MM-DD")
            if "#" in user_period:
                item_date = user_period.split("#")[1]
                if item_date in dates:
                    # Filter by request_type if specified
                    if request_type == "all" or item.get("request_type") == request_type:
                        filtered_items.append(item)
        items = filtered_items

        # Aggregate by user
        for item in items:
            uid = item.get("user_id")
            if not uid:
                continue

            if uid not in user_stats:
                user_stats[uid] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "requests": 0,
                }

            user_stats[uid]["input_tokens"] += item.get("input_tokens", 0)
            user_stats[uid]["output_tokens"] += item.get("output_tokens", 0)
            user_stats[uid]["total_tokens"] += item.get("total_tokens", 0)
            user_stats[uid]["requests"] += item.get("request_count", 0)

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
        return {"error": "An internal error has occurred."}
