-- This sql gathers all tokens issued and then identifies the client IP
-- Then it gathers main elements of the traffic for those IPs such as URI accessed even before the token was issued.
-- NOTE: This query requires 'labels' field which is not available in the current table structure

/*
-- Original version (requires labels field):
WITH t1 AS ( 
SELECT DISTINCT httpRequest.clientIp as clientip, label_item.name AS token_id
FROM duckdb.waf_logs_table,
UNNEST(CASE WHEN array_length(labels) >= 1
            THEN labels
            ELSE [{'name': 'NOLABEL'}]
        END) AS t(label_item)
WHERE to_timestamp(timestamp / 1000) >= current_date - INTERVAL 7 DAY
  AND label_item.name LIKE 'awswaf:managed:token:id:%'
)
SELECT DISTINCT 
    regexp_extract(labels::TEXT, 'awswaf:managed:token:id:(.*?)"', 1) AS issued_token,
    clientip, 
    responseCodeSent,
    httpRequest.uri, 
    to_timestamp(timestamp / 1000) as date_time,
    timestamp 
FROM t1, duckdb.waf_logs_table  
WHERE httpRequest.clientIp = t1.clientip  
  AND to_timestamp(timestamp / 1000) >= current_date - INTERVAL 7 DAY
ORDER BY clientip, timestamp DESC;
*/

-- Alternative query without labels (shows traffic by IP with request details):
SELECT DISTINCT 
    httpRequest.clientIp as clientip,
    responseCodeSent,
    httpRequest.uri, 
    to_timestamp(timestamp / 1000) as date_time,
    timestamp,
    terminatingRuleId,
    action
FROM duckdb.waf_logs_table  
WHERE to_timestamp(timestamp / 1000) >= current_date - INTERVAL 7 DAY
ORDER BY clientip, timestamp DESC;
