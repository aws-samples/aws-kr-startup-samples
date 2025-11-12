-- This sql identified for each waf token how many unique IPs were associated. Ideally this should be 1 or 2. 
-- If the token has values > 2, the IPs associated with that token should be further analysed for possible fraud.
-- NOTE: This query requires 'labels' field which is not available in the current table structure
-- You would need to add labels field to use this query

/*
-- Original Athena version (requires labels field):
SELECT label_item.name, COUNT(DISTINCT httpRequest.clientIp) as numberOfRequests
FROM duckdb.waf_logs_table,
UNNEST(CASE WHEN array_length(labels) >= 1
            THEN labels
            ELSE [{'name': 'NOLABEL'}]
        END) AS t(label_item)
WHERE to_timestamp(timestamp / 1000) >= current_date - INTERVAL 7 DAY
  AND label_item.name LIKE 'awswaf:managed:token:id:%'
GROUP BY label_item.name 
ORDER BY label_item.name;
*/

-- Alternative query without labels (counts unique IPs per terminating rule):
SELECT terminatingRuleId, COUNT(DISTINCT httpRequest.clientIp) as numberOfUniqueIPs
FROM duckdb.waf_logs_table
WHERE to_timestamp(timestamp / 1000) >= current_date - INTERVAL 7 DAY
GROUP BY terminatingRuleId 
ORDER BY terminatingRuleId;
