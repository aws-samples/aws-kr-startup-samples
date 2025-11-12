-- this sql is used to identify all traffic received from a single client IP or range of IPs .
-- The results are group by the terminating rule id ,the URI and the arguments of the request and the associated labels that were attached to the requests.
-- The results are sorted by the number of requests in descending order.
-- The results are limited to the last 7 days.
-- Note: labels field not available in this table, using 'NOLABEL' as default

SELECT COUNT(*) AS countRequests, terminatingRuleId, httpRequest.uri, httpRequest.args, 'NOLABEL' as label_name
FROM duckdb.waf_logs_table
WHERE to_timestamp(timestamp / 1000) >= current_date - INTERVAL 7 DAY
  AND httpRequest.clientIp LIKE 'XXX.YYY%'  -- Replace XXX.YYY with actual IP prefix
GROUP BY terminatingRuleId, httpRequest.uri, httpRequest.args
ORDER BY COUNT(*) DESC;
