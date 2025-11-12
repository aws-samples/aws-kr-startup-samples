-- This sql is used to identify the top 10 IPs which have made most requests in the past 7 days.
-- It allows you to identify which IPs are making the most requests in your WAF logs.
-- This can help you troubleshoot issues with your WAF logs and identify which IPs are causing issues.
SELECT httpRequest.clientIp, COUNT(*) AS requests
FROM duckdb.waf_logs_table
WHERE to_timestamp(timestamp / 1000) >= current_date - INTERVAL 7 DAY
GROUP BY httpRequest.clientIp
ORDER BY requests DESC
LIMIT 10;
