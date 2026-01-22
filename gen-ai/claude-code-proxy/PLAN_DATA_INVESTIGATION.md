# Plan API Usage Data Investigation Guide

## Current Status

✅ **Frontend**: Empty state is now properly displayed when no Plan data exists
✅ **Backend**: Code correctly records `provider='plan'` for Plan API requests
✅ **API**: Endpoints support `provider` parameter filtering

## Why No Plan Data Might Appear

### 1. No Plan API Requests Made Yet
**Check**: Are users actually making requests through the proxy?
```sql
-- Check total request count
SELECT COUNT(*) FROM token_usage;

-- Check provider breakdown
SELECT provider, COUNT(*) FROM token_usage GROUP BY provider;
```

### 2. All Users Using `bedrock_only` Strategy
**Check**: User routing strategies
```sql
SELECT routing_strategy, COUNT(*) 
FROM users 
WHERE deleted_at IS NULL 
GROUP BY routing_strategy;
```

If all users have `routing_strategy='bedrock_only'`, they skip Plan API entirely.

### 3. Circuit Breaker Open for All Keys
**Check**: Circuit breaker is in-memory, so check logs for:
- "Circuit breaker open" messages
- Repeated Plan API failures (429, 500-504, timeouts)

**Note**: Circuit breaker state resets on backend restart.

### 4. Plan API Key Not Configured
**Check**: Environment variable
```bash
# In backend container or environment
echo $PROXY_PLAN_API_KEY
```

If not set, Plan API requests will fail with authentication errors.

### 5. All Requests Falling Back to Bedrock
**Check**: `is_fallback` flag in database
```sql
-- Check fallback rate
SELECT 
  provider,
  is_fallback,
  COUNT(*) as count
FROM token_usage
GROUP BY provider, is_fallback;
```

If you see `provider='bedrock'` with `is_fallback=true`, it means Plan API failed and fell back.

## Recommended Investigation Steps

### Step 1: Check Database
```sql
-- Total usage records
SELECT COUNT(*) FROM token_usage;

-- Provider breakdown
SELECT 
  provider,
  is_fallback,
  COUNT(*) as requests,
  SUM(total_tokens) as total_tokens
FROM token_usage
GROUP BY provider, is_fallback
ORDER BY provider, is_fallback;

-- Recent requests (last 24 hours)
SELECT 
  created_at,
  provider,
  is_fallback,
  model,
  total_tokens
FROM token_usage
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC
LIMIT 20;
```

### Step 2: Check User Configuration
```sql
-- User routing strategies
SELECT 
  id,
  name,
  routing_strategy,
  created_at
FROM users
WHERE deleted_at IS NULL;

-- Access keys with Bedrock keys
SELECT 
  ak.id,
  ak.user_id,
  u.name as user_name,
  u.routing_strategy,
  CASE WHEN bk.id IS NOT NULL THEN 'Yes' ELSE 'No' END as has_bedrock_key
FROM access_keys ak
JOIN users u ON ak.user_id = u.id
LEFT JOIN bedrock_keys bk ON bk.access_key_id = ak.id
WHERE ak.deleted_at IS NULL;
```

### Step 3: Check Backend Logs
Look for:
- Plan API authentication errors
- Circuit breaker state changes
- Fallback triggers
- Request routing decisions

```bash
# If using Docker
docker compose logs backend | grep -i "plan\|circuit\|fallback"

# If running locally
# Check uvicorn logs for similar patterns
```

### Step 4: Test Plan API Directly
```bash
# Test if Plan API key works
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $PROXY_PLAN_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-opus-4-20250514",
    "max_tokens": 10,
    "messages": [{"role": "user", "content": "Hi"}]
  }'
```

### Step 5: Make a Test Request Through Proxy
```bash
# Replace with your access key
ACCESS_KEY="ak_..."

curl http://localhost:8000/ak/$ACCESS_KEY/v1/messages \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-opus-4-20250514",
    "max_tokens": 10,
    "messages": [{"role": "user", "content": "Test"}]
  }'
```

Then check database:
```sql
SELECT * FROM token_usage ORDER BY created_at DESC LIMIT 1;
```

## Expected Behavior

### For `plan_first` Strategy (Default)
1. Request comes in → Try Plan API first
2. If Plan succeeds → Record with `provider='plan'`, `is_fallback=false`
3. If Plan fails (429, 500-504) → Try Bedrock → Record with `provider='bedrock'`, `is_fallback=true`

### For `bedrock_only` Strategy
1. Request comes in → Skip Plan API entirely
2. Go directly to Bedrock → Record with `provider='bedrock'`, `is_fallback=false`

## Code References

### Where `provider='plan'` is Set

**Non-streaming** (`backend/src/api/proxy_router.py:95`):
```python
await usage_recorder.record(ctx, response, latency_ms, request.model)
# Uses response.provider from ProxyRouter
```

**Streaming** (`backend/src/api/proxy_router.py:289`):
```python
await _record_streaming_usage(
    usage_recorder, ctx, usage, latency_ms, request.model,
    is_fallback=False,
    provider="plan",  # ← Explicitly set
)
```

### ProxyRouter Sets Provider (`backend/src/proxy/router.py:142-149`):
```python
def _success_response(
    self, provider: Provider, result: AdapterResponse, is_fallback: bool
) -> ProxyResponse:
    return ProxyResponse(
        success=True,
        response=result.response,
        usage=result.usage,
        provider=provider,  # ← Set here
        is_fallback=is_fallback,
        status_code=200,
    )
```

## Next Steps

1. Run the database queries above to see what data exists
2. Check user routing strategies
3. Verify `PROXY_PLAN_API_KEY` is configured
4. Check backend logs for errors
5. Make a test request and verify it's recorded

The frontend is working correctly - it's just waiting for Plan API usage data to appear in the database!
