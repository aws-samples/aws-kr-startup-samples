-- This sql is used to identify which are the most accessed URI for the last 7 days.
SELECT httpRequest.uri, COUNT(*) AS requests
FROM duckdb.waf_logs_table
WHERE to_timestamp(timestamp / 1000) >= current_date - INTERVAL 7 DAY
GROUP BY httpRequest.uri
ORDER BY requests DESC
LIMIT 10;
