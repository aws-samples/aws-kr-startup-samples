-- This sql identifies the count of requests group across client IP, the terminating rule and URI accessed
-- This would analyze the top talker client IP are accessing certain URIs for a large number of times and if its being ALLOW / BLOCK / CHALLENGE / CAPTCHA. 

SELECT COUNT(*) AS countRequests, httpRequest.clientIp, terminatingRuleId, httpRequest.uri
FROM duckdb.waf_logs_table 
WHERE to_timestamp(timestamp / 1000) >= current_date - INTERVAL 7 DAY
GROUP BY httpRequest.clientIp, terminatingRuleId, httpRequest.uri
ORDER BY COUNT(*) DESC;
