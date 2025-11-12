-- This sql retrieves all requests that were passed a specific waf token
-- This analysis is useful to determine if a token is being used to attack the site
-- NOTE: This query requires 'labels' field which is not available in the current table structure

/*
-- Original version (requires labels field):
SELECT *
FROM duckdb.waf_logs_table,
UNNEST(CASE WHEN array_length(labels) >= 1
            THEN labels
            ELSE [{'name': 'NOLABEL'}]
        END) AS t(label_item)
WHERE to_timestamp(timestamp / 1000) >= current_date - INTERVAL 7 DAY
  AND label_item.name = 'INSERT_THE_TOKEN_ID_HERE'
ORDER BY timestamp;
*/

-- Alternative query without labels (filter by specific terminating rule or request ID):
SELECT *
FROM duckdb.waf_logs_table
WHERE to_timestamp(timestamp / 1000) >= current_date - INTERVAL 7 DAY
  AND httpRequest.requestId = 'INSERT_REQUEST_ID_HERE'  -- Replace with specific request ID
ORDER BY timestamp;
