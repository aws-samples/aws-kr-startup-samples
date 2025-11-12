-- Bot analysis by IP (DuckDB version)
-- NOTE: This query requires 'labels' field for full bot analysis

-- Alternative query without labels (action analysis by IP):
SELECT
    httpRequest.clientIp,
    COUNT(*) AS total_requests,
    COUNT(CASE WHEN action = 'ALLOW' THEN 1 END) as allow_requests,
    COUNT(CASE WHEN action = 'BLOCK' THEN 1 END) as block_requests,
    COUNT(CASE WHEN action = 'CHALLENGE' THEN 1 END) as challenge_requests,
    terminatingRuleId
FROM duckdb.waf_logs_table
WHERE to_timestamp(timestamp / 1000) >= current_date - INTERVAL 7 DAY
GROUP BY httpRequest.clientIp, terminatingRuleId
ORDER BY total_requests DESC;
