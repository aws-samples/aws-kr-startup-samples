"""Datasource configuration models and constants."""
from typing import Dict, Any, List
from enum import Enum


class DatasourceType(Enum):
    """Supported datasource types."""
    PROMETHEUS = "prometheus"
    TEMPO = "tempo"
    LOKI = "loki"


class DatasourceConfigSchema:
    """Schema for datasource configuration structure."""
    
    @staticmethod
    def create_empty_config() -> Dict[str, Any]:
        """Create an empty datasource configuration structure."""
        return {
            'basic_info': {},
            'details': None,
            'labels': None
        }
    
    @staticmethod
    def get_supported_types() -> List[str]:
        """Get list of supported datasource types."""
        return [ds_type.value for ds_type in DatasourceType]


# Tool names used for datasource operations
REQUIRED_TOOLS = [
    "list_datasources", 
    "get_datasource_by_uid", 
    "list_prometheus_label_names", 
    "list_loki_label_names"
] 