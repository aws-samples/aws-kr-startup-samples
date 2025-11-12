-- Rate-based rule header threshold analysis (DuckDB version)
-- Similar to rbrclientipurithreshold but focused on headers

WITH header_stats AS (
  SELECT
    httpRequest.clientIp AS clientip,
    header.name as header_name,
    header.value as header_value,
    date_trunc('minute', to_timestamp(timestamp / 1000)) AS five_minute,
    COUNT(*) AS totalRequest
  FROM duckdb.waf_logs_table 
  CROSS JOIN UNNEST(httpRequest.headers) as t(header)
  WHERE to_timestamp(timestamp / 1000) >= current_date - INTERVAL 1 DAY
    AND LOWER(header.name) = 'user-agent'  -- Focus on user-agent header
  GROUP BY 1,2,3,4
)
SELECT 
  MIN(totalRequest) AS min, 
  MAX(totalRequest) AS max, 
  ROUND(AVG(totalRequest)) AS avg, 
  quantile_cont(totalRequest, 0.95) AS p95, 
  quantile_cont(totalRequest, 0.99) AS p99, 
  SUM(totalRequest) AS totalRequests, 
  clientip,
  header_name,
  header_value
FROM header_stats
GROUP BY clientip, header_name, header_value
ORDER BY max DESC;
