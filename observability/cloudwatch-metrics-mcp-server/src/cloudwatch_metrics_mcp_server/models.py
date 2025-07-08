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

from cloudwatch_metrics_mcp_server.common import epoch_seconds_to_utc_iso
from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, List, Optional


class Dimension(BaseModel):
    """Represents a CloudWatch metric dimension."""

    name: str = Field(..., description='The name of the dimension')
    value: str = Field(..., description='The value of the dimension')


class MetricMetadata(BaseModel):
    """Represents metric information with dimensions."""

    metricName: str = Field(..., description='The name of the metric')
    namespace: str = Field(..., description='The CloudWatch namespace')
    dimensions: List[Dimension] = Field(default_factory=list, description='List of metric dimensions')


class Datapoint(BaseModel):
    """Represents an individual metric data point."""

    timestamp: str = Field(..., description='ISO 8601 timestamp of the data point')
    sampleCount: Optional[float] = Field(None, description='The number of samples used for the statistic')
    average: Optional[float] = Field(None, description='The average value')
    sum: Optional[float] = Field(None, description='The sum of values')
    minimum: Optional[float] = Field(None, description='The minimum value')
    maximum: Optional[float] = Field(None, description='The maximum value')
    unit: Optional[str] = Field(None, description='The unit of measurement')

    @field_validator('timestamp', mode='before')
    @classmethod
    def convert_to_iso8601(cls, v):
        """If value passed is a datetime or timestamp, convert to an ISO timestamp string."""
        if hasattr(v, 'timestamp'):
            return epoch_seconds_to_utc_iso(v.timestamp())
        elif isinstance(v, (int, float)):
            return epoch_seconds_to_utc_iso(v)
        return v


class MetricStatistics(BaseModel):
    """Represents statistical data for a metric."""

    label: str = Field(..., description='The label for the metric')
    datapoints: List[Datapoint] = Field(default_factory=list, description='List of data points')


class MetricStat(BaseModel):
    """Represents a metric statistic configuration."""

    metric: Dict[str, Any] = Field(..., description='The metric information')
    period: int = Field(..., description='The period in seconds')
    stat: str = Field(..., description='The statistic type')
    unit: Optional[str] = Field(None, description='The unit of measurement')


class MetricDataQuery(BaseModel):
    """Represents a metric data query."""

    id: str = Field(..., description='A unique identifier for the query')
    metricStat: Optional[MetricStat] = Field(None, description='The metric stat configuration')
    expression: Optional[str] = Field(None, description='The math expression')
    label: Optional[str] = Field(None, description='A human-readable label')
    returnData: Optional[bool] = Field(True, description='Whether to return data for this query')
    period: Optional[int] = Field(None, description='The period in seconds')
    accountId: Optional[str] = Field(None, description='The account ID')


class MetricDataResult(BaseModel):
    """Represents metric data query results."""

    id: str = Field(..., description='The unique identifier for the query')
    label: Optional[str] = Field(None, description='A human-readable label')
    timestamps: List[str] = Field(default_factory=list, description='List of ISO 8601 timestamps')
    values: List[float] = Field(default_factory=list, description='List of values')
    statusCode: Optional[str] = Field(None, description='The status code')
    messages: Optional[List[Dict[str, str]]] = Field(None, description='Any messages')

    @field_validator('timestamps', mode='before')
    @classmethod
    def convert_timestamps_to_iso8601(cls, v):
        """Convert timestamps to ISO 8601 format."""
        if not v:
            return []
        converted = []
        for timestamp in v:
            if hasattr(timestamp, 'timestamp'):
                converted.append(epoch_seconds_to_utc_iso(timestamp.timestamp()))
            elif isinstance(timestamp, (int, float)):
                converted.append(epoch_seconds_to_utc_iso(timestamp))
            else:
                converted.append(timestamp)
        return converted


class MetricData(BaseModel):
    """Represents metric data response."""

    metric_data_results: List[MetricDataResult] = Field(default_factory=list, description='List of metric data results')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    messages: Optional[List[Dict[str, str]]] = Field(None, description='Any messages')


class MetricList(BaseModel):
    """Represents a list of metrics."""

    metrics: List[MetricMetadata] = Field(default_factory=list, description='List of metrics')
    next_token: Optional[str] = Field(None, description='Token for pagination')


class NamespaceList(BaseModel):
    """Represents a list of namespaces."""

    namespaces: List[str] = Field(default_factory=list, description='List of CloudWatch namespaces')
    next_token: Optional[str] = Field(None, description='Token for pagination')


class DimensionMetadata(BaseModel):
    """Represents dimension information."""

    dimension_name: str = Field(..., description='The name of the dimension')
    dimension_values: List[str] = Field(default_factory=list, description='Available values for this dimension')
    namespace: str = Field(..., description='The CloudWatch namespace')


class DimensionList(BaseModel):
    """Represents a list of dimensions."""

    dimensions: List[DimensionMetadata] = Field(default_factory=list, description='List of dimensions')
    next_token: Optional[str] = Field(None, description='Token for pagination')


 