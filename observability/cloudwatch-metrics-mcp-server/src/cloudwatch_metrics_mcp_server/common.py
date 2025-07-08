# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from typing import Any, Dict, List, Set


def remove_null_values(d: Dict):
    """Return a new dictionary with the key-value pair of any null value removed."""
    return {k: v for k, v in d.items() if v}


def epoch_ms_to_utc_iso(ms: int) -> str:
    """Convert milliseconds since epoch to an ISO 8601 timestamp string."""
    return datetime.datetime.fromtimestamp(ms / 1000.0, tz=datetime.timezone.utc).isoformat()


def epoch_seconds_to_utc_iso(seconds: int) -> str:
    """Convert seconds since epoch to an ISO 8601 timestamp string."""
    return datetime.datetime.fromtimestamp(seconds, tz=datetime.timezone.utc).isoformat()


def normalize_dimensions(dimensions: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Normalize dimension format to consistent structure."""
    if not dimensions:
        return []
    
    normalized = []
    for dim in dimensions:
        if 'Name' in dim and 'Value' in dim:
            normalized.append({'Name': dim['Name'], 'Value': dim['Value']})
        elif 'name' in dim and 'value' in dim:
            normalized.append({'Name': dim['name'], 'Value': dim['value']})
    
    return normalized


def extract_namespaces_from_metrics(metrics: List[Dict]) -> Set[str]:
    """Extract unique namespaces from a list of metrics."""
    return {metric.get('Namespace') for metric in metrics if metric.get('Namespace')}


def build_metric_data_query_dict(query_obj) -> Dict[str, Any]:
    """Build a dictionary representation of a MetricDataQuery for AWS API."""
    query_dict = {'Id': query_obj.id}
    
    if query_obj.metricStat:
        metric_stat = {
            'Metric': query_obj.metricStat.metric,
            'Period': query_obj.metricStat.period,
            'Stat': query_obj.metricStat.stat
        }
        
        if query_obj.metricStat.unit:
            metric_stat['Unit'] = query_obj.metricStat.unit
        
        query_dict['MetricStat'] = metric_stat
    
    if query_obj.expression:
        query_dict['Expression'] = query_obj.expression
    
    if query_obj.label:
        query_dict['Label'] = query_obj.label
    
    if query_obj.returnData is not None:
        query_dict['ReturnData'] = query_obj.returnData
    
    if query_obj.period:
        query_dict['Period'] = query_obj.period
    
    if query_obj.accountId:
        query_dict['AccountId'] = query_obj.accountId
    
    return query_dict

 