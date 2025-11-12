-- Rate-based rule client IP and URI threshold analysis (DuckDB version)
-- This query analyzes request patterns by client IP and URI with statistical thresholds

WITH t1 AS (
  SELECT
    httpRequest.clientIp AS clientip, 
    httpRequest.uri AS uri,
    date_trunc('minute', to_timestamp(timestamp / 1000)) AS five_minute,
    COUNT(httpRequest.clientIp) AS totalRequest
  FROM duckdb.waf_logs_table
  WHERE to_timestamp(timestamp / 1000) >= current_date - INTERVAL 1 DAY
    -- AND to_timestamp(timestamp / 1000) >= '2024-07-11 00:00:00'::timestamp  -- Optional start time
    -- AND to_timestamp(timestamp / 1000) <= '2024-07-11 16:00:00'::timestamp  -- Optional end time
  GROUP BY 1,2,3
)
SELECT 
  MIN(totalRequest) AS min, 
  MAX(totalRequest) AS max, 
  ROUND(AVG(totalRequest)) AS avg, 
  quantile_cont(totalRequest, 0.95) AS p95, 
  quantile_cont(totalRequest, 0.99) AS p99, 
  SUM(totalRequest) AS totalRequests, 
  clientip, 
  uri
FROM t1
GROUP BY clientip, uri
ORDER BY max DESC;
