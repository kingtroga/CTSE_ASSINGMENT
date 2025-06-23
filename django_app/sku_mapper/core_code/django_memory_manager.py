# sku_mapper/core/django_memory_manager.py
# =============================================================================
# Django Memory Manager - Replaces memory_manager.py
# =============================================================================

import pandas as pd
from typing import Dict, List, Optional
from .logger import WMSLogger
from .data_validator import DataValidator
import sys
from pathlib import Path



try:
    from core.models import (
        Product, Warehouse, Inventory, Marketplace, SKUMapping, 
        ComboProduct, ComboProductItem
    )
except ImportError:
    # Fallback if models not available (for testing)
    print("Warning: Django models not available. Using fallback mode.")
    Product = Warehouse = Inventory = Marketplace = SKUMapping = None
    ComboProduct = ComboProductItem = None

class DjangoMemoryManager:
    """Django ORM-based memory manager - replaces CSV file operations"""
    
    def __init__(self, logger: WMSLogger, validator: DataValidator):
        self.logger = logger
        self.validator = validator
        self._ensure_django_connection()
    
    def _ensure_django_connection(self):
        """Ensure Django models are available"""
        try:
            if Product is not None:
                # Test database connection
                Product.objects.first()
                self.logger.log_process("DJANGO", "CONNECTED", "Django ORM connection established")
            else:
                self.logger.log_process("DJANGO", "WARNING", "Django models not available - using fallback mode")
        except Exception as e:
            self.logger.log_process("DJANGO", "ERROR", f"Django connection failed: {str(e)}")
            raise
    
    def load_csv_with_fallback(self, memory_path, master_path) -> pd.DataFrame:
        """Load data from Django models (replaces CSV loading)"""
        try:
            # Determine data type based on file path
            if 'mapping' in str(memory_path) or 'mapping' in str(master_path):
                return self._load_sku_mappings_from_django()
            elif 'combo' in str(memory_path) or 'combo' in str(master_path):
                return self._load_combo_data_from_django()
            elif 'inventory' in str(memory_path) or 'inventory' in str(master_path):
                return self._load_inventory_from_django()
            else:
                # Fallback to original CSV method
                return pd.read_csv(master_path)
                
        except Exception as e:
            self.logger.log_process("DJANGO", "ERROR", f"Failed to load data: {str(e)}")
            # Fallback to CSV if Django fails
            try:
                return pd.read_csv(master_path)
            except:
                return pd.DataFrame()
    
    def _load_sku_mappings_from_django(self) -> pd.DataFrame:
        """Load SKU mappings from Django models"""
        try:
            if SKUMapping is None:
                return pd.DataFrame()
            
            # Get all active SKU mappings
            mappings = SKUMapping.objects.select_related('product', 'marketplace').filter(
                status='ACTIVE'
            )
            
            # Convert to DataFrame
            mapping_data = []
            for mapping in mappings:
                mapping_data.append({
                    'sku': mapping.sku,
                    'msku': mapping.product.msku,
                    'panels': mapping.marketplace.code,
                    'status': mapping.status,
                    'marketplace_price': float(mapping.marketplace_price) if mapping.marketplace_price else None,
                    'product_name': mapping.product.product_name,
                    'created_at': mapping.created_at,
                    'updated_at': mapping.updated_at
                })
            
            df = pd.DataFrame(mapping_data)
            self.logger.log_process("DJANGO", "LOADED", f"SKU mappings loaded: {len(df)} records")
            return df
            
        except Exception as e:
            self.logger.log_process("DJANGO", "ERROR", f"Failed to load SKU mappings: {str(e)}")
            return pd.DataFrame()
    
    def _load_combo_data_from_django(self) -> pd.DataFrame:
        """Load combo product data from Django models"""
        try:
            if ComboProduct is None:
                return pd.DataFrame()
            
            # Get all active combo products with their items
            combos = ComboProduct.objects.filter(is_active=True).prefetch_related('combo_items__product')
            
            combo_data = []
            for combo in combos:
                row = {
                    'Combo': combo.combo_sku,
                    'combo_name': combo.combo_name,
                    'marketplace': combo.marketplace.code,
                    'combo_price': float(combo.combo_price),
                    'is_auto_split': combo.is_auto_split,
                    'total_items': combo.total_items
                }
                
                # Add SKU columns (SKU1, SKU2, etc.)
                for i, item in enumerate(combo.combo_items.all(), 1):
                    row[f'SKU{i}'] = item.product.msku
                    row[f'QTY{i}'] = item.quantity
                
                combo_data.append(row)
            
            df = pd.DataFrame(combo_data)
            self.logger.log_process("DJANGO", "LOADED", f"Combo data loaded: {len(df)} combos")
            return df
            
        except Exception as e:
            self.logger.log_process("DJANGO", "ERROR", f"Failed to load combo data: {str(e)}")
            return pd.DataFrame()
    
    def _load_inventory_from_django(self) -> pd.DataFrame:
        """Load inventory data from Django models"""
        try:
            if Inventory is None or Product is None or Warehouse is None:
                return pd.DataFrame()
            
            # Get all inventory records with related data
            inventory_records = Inventory.objects.select_related('product', 'warehouse').all()
            
            # Convert to DataFrame format matching your original structure
            inventory_data = []
            
            # Group by product to create wide format (one row per product with warehouse columns)
            products = Product.objects.all()
            warehouses = Warehouse.objects.all()
            
            for product in products:
                row = {
                    'msku': product.msku,
                    'product_name': product.product_name,
                    'category': product.category or '',
                    'brand': product.brand or '',
                    'is_active': product.is_active,
                    'total_stock': 0
                }
                
                # Add warehouse columns
                for warehouse in warehouses:
                    try:
                        inventory = Inventory.objects.get(product=product, warehouse=warehouse)
                        row[warehouse.code] = inventory.current_stock
                        row['total_stock'] += inventory.current_stock
                    except Inventory.DoesNotExist:
                        row[warehouse.code] = 0
                
                inventory_data.append(row)
            
            df = pd.DataFrame(inventory_data)
            self.logger.log_process("DJANGO", "LOADED", f"Inventory data loaded: {len(df)} products")
            return df
            
        except Exception as e:
            self.logger.log_process("DJANGO", "ERROR", f"Failed to load inventory: {str(e)}")
            return pd.DataFrame()
    
    def save_to_memory(self, df: pd.DataFrame, memory_path) -> bool:
        """Save dataframe to Django models (replaces CSV saving)"""
        try:
            # For now, we'll skip saving back to Django to avoid complexity
            # In production, you might want to implement this for caching
            self.logger.log_process("DJANGO", "SKIPPED", f"Django save skipped for: {memory_path}")
            return True
            
        except Exception as e:
            self.logger.log_process("DJANGO", "ERROR", f"Failed to save to Django: {str(e)}")
            return False
    
    def load_mapping_data(self, additional_mapping_path: str = None, replace_existing: bool = False) -> pd.DataFrame:
        """Load mapping data with option to add additional mappings"""
        try:
            # Load base mapping data from Django
            base_mapping = self._load_sku_mappings_from_django()
            base_mapping = self.validator.normalize_column_names(base_mapping)
            
            if additional_mapping_path and pd.read_csv(additional_mapping_path) is not None:
                additional_mapping = pd.read_csv(additional_mapping_path)
                additional_mapping = self.validator.normalize_column_names(additional_mapping)
                
                # Validate required columns
                is_valid, error_msg = self.validator.validate_required_columns(
                    additional_mapping, ['sku', 'msku', 'panels']
                )
                
                if not is_valid:
                    self.logger.log_process("DJANGO", "ERROR", f"Additional mapping validation failed: {error_msg}")
                    return base_mapping
                
                # Clean additional mapping
                additional_mapping = self.validator.clean_dataframe(
                    additional_mapping, ['sku', 'panels']
                )
                
                if replace_existing:
                    final_mapping = additional_mapping
                    self.logger.log_process("DJANGO", "REPLACED", "Mapping data replaced")
                else:
                    final_mapping = pd.concat([base_mapping, additional_mapping]).drop_duplicates(['sku', 'panels'])
                    self.logger.log_process("DJANGO", "MERGED", "Additional mapping data merged")
                
                # Optionally save updated mapping back to Django here
                return final_mapping
            
            return base_mapping
            
        except Exception as e:
            self.logger.log_process("DJANGO", "ERROR", f"Failed to load mapping data: {str(e)}")
            return pd.DataFrame()
    
    def update_inventory_stock(self, msku: str, warehouse_code: str, quantity_change: int, 
                              movement_type: str = 'OUTBOUND', reference: str = None) -> bool:
        """Update inventory stock levels in Django"""
        try:
            if Product is None or Warehouse is None or Inventory is None:
                return False
            
            # Get product and warehouse
            product = Product.objects.get(msku=msku)
            warehouse = Warehouse.objects.get(code=warehouse_code)
            
            # Get or create inventory record
            inventory, created = Inventory.objects.get_or_create(
                product=product,
                warehouse=warehouse,
                defaults={'current_stock': 0}
            )
            
            # Update stock
            inventory.current_stock += quantity_change
            inventory.save()
            
            self.logger.log_process("DJANGO", "STOCK_UPDATED", 
                                  f"{msku} @ {warehouse_code}: {quantity_change} (new: {inventory.current_stock})")
            
            return True
            
        except Exception as e:
            self.logger.log_process("DJANGO", "ERROR", f"Failed to update stock: {str(e)}")
            return False