-- This sql is categorizing all requests based on the labels attached such as relating to bots, amazon managed rules, types of requests
-- NOTE: This query requires 'labels' field which is not available in the current table structure

/*
-- Original version would require labels field for detailed bot analysis
-- This is a complex query that analyzes various AWS managed rule groups
*/

-- Alternative query without labels (basic action analysis):
SELECT
    DATE(to_timestamp(timestamp / 1000)) as date,
    COUNT(DISTINCT httpRequest.requestId) AS total_requests,
    COUNT(DISTINCT CASE WHEN action = 'CHALLENGE' THEN httpRequest.requestId END) as challenge_requests,
    COUNT(DISTINCT CASE WHEN action = 'ALLOW' THEN httpRequest.requestId END) as allow_requests,
    COUNT(DISTINCT CASE WHEN action = 'BLOCK' THEN httpRequest.requestId END) as block_requests,
    COUNT(DISTINCT CASE WHEN action = 'CAPTCHA' THEN httpRequest.requestId END) as captcha_requests
FROM duckdb.waf_logs_table
WHERE to_timestamp(timestamp / 1000) >= current_date - INTERVAL 7 DAY
GROUP BY DATE(to_timestamp(timestamp / 1000))
ORDER BY date;
