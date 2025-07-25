"""Caching logic for datasource configurations."""
from typing import Dict, Any, Optional


class DatasourceCache:
    """Manages caching of datasource configurations."""
    
    def __init__(self):
        """Initialize the cache."""
        self.config: Dict[str, Any] = {}
        self._is_loaded = False
    
    def is_loaded(self) -> bool:
        """Check if datasource configuration has been loaded."""
        return self._is_loaded
    
    def get_config(self, ds_type: str) -> Optional[Dict[str, Any]]:
        """Get cached configuration for a specific datasource type."""
        return self.config.get(ds_type)
    
    def get_all_configs(self) -> Dict[str, Any]:
        """Get all cached datasource configurations."""
        return self.config
    
    def set_config(self, config: Dict[str, Any]):
        """Set the cached configuration."""
        self.config = config
        self._is_loaded = True
    
    def clear_cache(self):
        """Clear the cache."""
        self.config = {}
        self._is_loaded = False


# Global singleton pattern implementation
_datasource_config_instance: Optional['DatasourceManager'] = None


def get_datasource_config():
    """Get the global datasource configuration instance."""
    global _datasource_config_instance
    if _datasource_config_instance is None:
        from .manager import DatasourceManager
        _datasource_config_instance = DatasourceManager()
    return _datasource_config_instance


def load_datasources_config() -> Dict[str, Any]:
    """Load and return datasource configurations."""
    return get_datasource_config().load_datasources_config()


def get_datasource_by_type(ds_type: str) -> Optional[Dict[str, Any]]:
    """Get datasource configuration by type."""
    return get_datasource_config().get_datasource_config(ds_type) 