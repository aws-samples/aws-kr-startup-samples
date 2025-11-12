-- WAF token analysis (DuckDB version)
-- NOTE: This query requires 'labels' field for token analysis

-- Alternative query without labels (request analysis):
SELECT
    httpRequest.clientIp,
    COUNT(*) as request_count,
    COUNT(DISTINCT httpRequest.uri) as unique_uris,
    terminatingRuleId,
    action
FROM duckdb.waf_logs_table
WHERE to_timestamp(timestamp / 1000) >= current_date - INTERVAL 7 DAY
GROUP BY httpRequest.clientIp, terminatingRuleId, action
ORDER BY request_count DESC;
