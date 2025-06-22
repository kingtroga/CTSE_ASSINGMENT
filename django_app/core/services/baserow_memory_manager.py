import pandas as pd
import requests
import logging
from typing import Dict, List, Optional
from pathlib import Path
from django.conf import settings
from django.db import transaction

# Import your Django models
from core.models import (
    Product, Warehouse, Marketplace, Inventory, 
    SKUMapping, ComboProduct, ComboProductItem
)

logger = logging.getLogger(__name__)

class BaserowMemoryManager:
    """
    Replaces the original memory_manager.py with Django+Baserow integration
    Maintains compatibility with original SKU_Mapper system
    """
    
    def __init__(self):
        # Baserow API configuration
        self.base_url = getattr(settings, 'BASEROW_BASE_URL', 'https://api.baserow.io')
        self.api_token = getattr(settings, 'BASEROW_API_TOKEN', '')
        
        # Table IDs (set these in Django settings after creating Baserow tables)
        self.table_ids = {
            'sku_mappings': getattr(settings, 'BASEROW_SKU_MAPPING_TABLE_ID', ''),
            'inventory': getattr(settings, 'BASEROW_INVENTORY_TABLE_ID', ''),
            'combo_products': getattr(settings, 'BASEROW_COMBO_TABLE_ID', ''),
        }
        
        self.headers = {
            'Authorization': f'Token {self.api_token}',
            'Content-Type': 'application/json'
        }
        
        # Memory paths (for compatibility with original system)
        self.memory_dir = Path('memory')
        self.memory_dir.mkdir(exist_ok=True)
        
        self.memory_files = {
            'mappings': self.memory_dir / 'sku_mappings_memory.csv',
            'inventory': self.memory_dir / 'inventory_memory.csv',
            'combos': self.memory_dir / 'combo_sku_memory.csv'
        }
    
    def _make_baserow_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make HTTP request to Baserow API"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=self.headers, params=data)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            elif method.upper() == 'PATCH':
                response = requests.patch(url, headers=self.headers, json=data)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Baserow API request failed: {str(e)}")
            return {}