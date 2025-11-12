-- This sql is to show the count of IPs matching a label over a period of 7 days. 
-- If a request has no label attached, then it would be recorded against NOLABEL
-- NOTE: This query requires 'labels' field which is not available in the current table structure

/*
-- Original version (requires labels field):
SELECT COUNT(*) AS count, httpRequest.clientIp, label_item.name
FROM duckdb.waf_logs_table,
UNNEST(CASE WHEN array_length(labels) >= 1
            THEN labels
            ELSE [{'name': 'NOLABEL'}]
        END) AS t(label_item)
WHERE to_timestamp(timestamp / 1000) >= current_date - INTERVAL 7 DAY
GROUP BY httpRequest.clientIp, label_item.name
ORDER BY clientIp;
*/

-- Alternative query without labels (group by terminating rule):
SELECT COUNT(*) AS count, httpRequest.clientIp, terminatingRuleId as rule_name
FROM duckdb.waf_logs_table
WHERE to_timestamp(timestamp / 1000) >= current_date - INTERVAL 7 DAY
GROUP BY httpRequest.clientIp, terminatingRuleId
ORDER BY httpRequest.clientIp;
