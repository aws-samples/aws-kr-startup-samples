"""Datasource configuration management and loading logic."""
from typing import Dict, Any, List, Optional
import json
from strands import Agent
from observability_agent.mcp import get_tool_by_name
from .models import REQUIRED_TOOLS, DatasourceConfigSchema
from .cache import DatasourceCache


class DatasourceManager:
    """Manages and loads datasource configurations from MCP servers."""
    
    def __init__(self):
        """Initialize the datasource configuration manager."""
        self.cache = DatasourceCache()
        
        # Collect available tools for the agent
        available_tools = []
        for tool_name in REQUIRED_TOOLS:
            tool = get_tool_by_name(tool_name)
            if tool:
                available_tools.append(tool)
        
        self.agent = Agent(
            system_prompt="You are a specialized observability agent which can fetch datasource configurations from MCP servers.",
            tools=available_tools
        )
    
    def is_loaded(self) -> bool:
        """Check if datasource configuration has been loaded."""
        return self.cache.is_loaded()
    
    def load_datasources_config(self) -> Dict[str, Any]:
        """Load datasource configuration from MCP servers.
        
        This function:
        1. Gets all Grafana datasources using list_datasources
        2. Gets details about Prometheus, Tempo, Loki datasources (one each) using get_datasource_by_uid
        3. If more than one for each category, uses the first one with lower id
        4. For prometheus and loki datasources, gets label names
        5. Saves information as dictionary with type as key
        
        Returns:
            Dict[str, Any]: Dictionary with datasource type as key and configuration as value
        """
        if self.cache.is_loaded():
            return self.cache.get_all_configs()
            
        print("Loading datasources configuration...")
        
        try:
            # Step 1: Get all datasources
            print("Fetching all datasources...")
            all_datasources_result = self.agent.tool.list_datasources()
            
            # Extract JSON from MCP response format
            all_datasources = json.loads(all_datasources_result['content'][0]['text'])
            
            print(f"Found {len(all_datasources) if isinstance(all_datasources, list) else 'unknown'} datasources")
            
            # Step 2: Filter and sort datasources by type
            datasources_by_type = self._categorize_datasources(all_datasources)
            
            # Step 3: Get detailed configuration for each type
            config = {}
            for ds_type, datasources in datasources_by_type.items():
                if datasources:
                    selected_ds = datasources[0]  # Use first (lowest id)
                    print(f"Loading {ds_type} datasource: {selected_ds.get('name', 'unnamed')} (id: {selected_ds.get('id')})")
                    config[ds_type] = self._load_datasource_details(selected_ds, ds_type)
            
            self.cache.set_config(config)
            print("Datasource configuration loaded successfully!")
            print(f"Loaded configuration for: {list(config.keys())}")
            
            return config
            
        except Exception as e:
            print(f"Error loading datasources configuration: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _categorize_datasources(self, all_datasources: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize and sort datasources by type."""
        prometheus_datasources = []
        tempo_datasources = []
        loki_datasources = []
        
        if isinstance(all_datasources, list):
            for ds in all_datasources:
                if isinstance(ds, dict):
                    ds_type = ds.get('type', '').lower()
                    if ds_type == 'prometheus':
                        prometheus_datasources.append(ds)
                    elif ds_type == 'tempo':
                        tempo_datasources.append(ds)
                    elif ds_type == 'loki':
                        loki_datasources.append(ds)
        
        # Sort by id and take the first one (lowest id) for each type
        prometheus_datasources.sort(key=lambda x: x.get('id', float('inf')))
        tempo_datasources.sort(key=lambda x: x.get('id', float('inf')))
        loki_datasources.sort(key=lambda x: x.get('id', float('inf')))
        
        print(f"Found {len(prometheus_datasources)} Prometheus, {len(tempo_datasources)} Tempo, {len(loki_datasources)} Loki datasources")
        
        return {
            'prometheus': prometheus_datasources,
            'tempo': tempo_datasources,
            'loki': loki_datasources
        }
    
    def _load_datasource_details(self, datasource: Dict[str, Any], ds_type: str) -> Dict[str, Any]:
        """Load detailed configuration for a specific datasource.
        
        Args:
            datasource: Basic datasource information
            ds_type: Type of datasource ('prometheus', 'tempo', 'loki')
            
        Returns:
            Dict[str, Any]: Detailed datasource configuration
        """
        config = DatasourceConfigSchema.create_empty_config()
        config['basic_info'] = datasource
        
        # Get detailed datasource information
        if datasource.get('uid'):
            try:
                print(f"Fetching details for {ds_type} datasource uid: {datasource.get('uid')}")
                details_result = self.agent.tool.get_datasource_by_uid(uid=datasource['uid'])
                
                # Extract JSON from MCP response format
                config['details'] = json.loads(details_result['content'][0]['text'])
                    
            except Exception as e:
                print(f"Error getting details for {ds_type} datasource: {e}")
        
        # Get label names for Prometheus and Loki
        if ds_type in ['prometheus', 'loki']:
            config['labels'] = self._load_label_names(datasource, ds_type)
        
        return config
    
    def _load_label_names(self, datasource: Dict[str, Any], ds_type: str) -> Optional[List[str]]:
        """Load label names for Prometheus or Loki datasource.
        
        Args:
            datasource: Datasource information
            ds_type: Type of datasource ('prometheus' or 'loki')
            
        Returns:
            Optional[List[str]]: List of label names or None if failed
        """
        try:
            print(f"Fetching label names for {ds_type} datasource")
            
            if ds_type == 'prometheus':
                labels_result = self.agent.tool.list_prometheus_label_names(datasourceUid=datasource.get('uid', ''))
            elif ds_type == 'loki':
                labels_result = self.agent.tool.list_loki_label_names(datasourceUid=datasource.get('uid', ''))
            else:
                return None
            
            # Extract JSON from MCP response format
            labels = json.loads(labels_result['content'][0]['text'])
            
            print(f"Found {len(labels) if isinstance(labels, list) else 'unknown'} labels for {ds_type}")
            return labels
            
        except Exception as e:
            print(f"Error getting label names for {ds_type}: {e}")
            return None
    
    def get_datasource_config(self, ds_type: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific datasource type.
        
        Args:
            ds_type: Type of datasource ('prometheus', 'tempo', 'loki')
            
        Returns:
            Optional[Dict[str, Any]]: Datasource configuration or None if not found
        """
        if not self.cache.is_loaded():
            self.load_datasources_config()
        return self.cache.get_config(ds_type)
    
    def get_all_configs(self) -> Dict[str, Any]:
        """Get all datasource configurations.
        
        Returns:
            Dict[str, Any]: All datasource configurations
        """
        if not self.cache.is_loaded():
            self.load_datasources_config()
        return self.cache.get_all_configs()
    
    def reload_config(self) -> Dict[str, Any]:
        """Force reload of datasource configuration.
        
        Returns:
            Dict[str, Any]: Reloaded datasource configurations
        """
        self.cache.clear_cache()
        return self.load_datasources_config() 