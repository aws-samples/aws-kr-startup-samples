-- Traffic analysis by rate-based rule URI (DuckDB version)
-- This query analyzes traffic patterns by client IP, terminating rule, and URI
-- Aggregated by 5-minute intervals for time-series analysis

SELECT
  httpRequest.clientIp AS clientip,
  terminatingRuleId,
  date_trunc('minute', to_timestamp(timestamp / 1000)) AS five_minute,
  rateBasedRuleList,
  action,
  httpRequest.uri,
  COUNT(*) AS numberOfRequests
FROM duckdb.waf_logs_table
WHERE to_timestamp(timestamp / 1000) >= current_date - INTERVAL 10 DAY
  -- AND terminatingRuleType = 'RATE_BASED'  -- Uncomment if you want only rate-based rules
GROUP BY 1,2,3,4,5,6
ORDER BY five_minute;
