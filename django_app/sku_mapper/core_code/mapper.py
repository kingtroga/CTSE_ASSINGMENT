# sku_mapper/core/mapper.py
# =============================================================================
# Updated SKU Mapper with Django Integration
# =============================================================================
import traceback
import pandas as pd
from ..utils.constants import Config
from .logger import WMSLogger
from .data_validator import DataValidator
from .django_memory_manager import DjangoMemoryManager  # NEW: Django memory manager
from .combo_handler import ComboHandler
from .inventory_manager import InventoryManager
from ..processors.output_processor import OutputProcessor

class SKUMapper:
    """Main SKU Mapper class - orchestrates all operations with Django integration"""
    
    def __init__(self, report_data_df: pd.DataFrame, data_type: str = 'outbound', use_django: bool = True):
        """Initialize SKU Mapper with report data"""
        self.report_data_df = report_data_df.copy()
        self.data_type = data_type
        self.use_django = use_django  # NEW: Flag to enable/disable Django
        
        # Initialize components
        self.logger = WMSLogger()
        self.validator = DataValidator(self.logger)
        
        # NEW: Use Django memory manager if enabled
        if self.use_django:
            self.memory_manager = DjangoMemoryManager(self.logger, self.validator)
        else:
            # Fallback to original CSV memory manager
            from .memory_manager import MemoryManager
            self.memory_manager = MemoryManager(self.logger, self.validator)
        
        self.output_processor = OutputProcessor(self.logger)
        
        # Data attributes
        self.mapping_df = None
        self.combo_handler = None
        self.inventory_manager = None
        self.processed_df = None
        self.unmapped_skus = []
        
        # SKU mapping hashtable
        self._sku_hashtable = None
        
        # Initialize system
        self._initialize_system()
    
    def _initialize_system(self):
        """Initialize all system components"""
        try:
            if self.use_django:
                # NEW: Django-based initialization
                self.logger.log_process("SYSTEM", "DJANGO_MODE", "Initializing with Django ORM")
                
                # Load mapping data from Django
                self.mapping_df = self.memory_manager.load_csv_with_fallback(
                    'memory/sku_mappings_memory.csv',  # Dummy path - will use Django
                    'clean_data/sku_mappings_final_clean.csv'  # Fallback path
                )
                
                # Load combo data from Django
                combo_df = self.memory_manager.load_csv_with_fallback(
                    'memory/combo_sku_memory.csv',  # Dummy path - will use Django
                    'clean_data/combo_sku_clean.csv'  # Fallback path
                )
                
                # Load inventory data from Django
                inventory_df = self.memory_manager.load_csv_with_fallback(
                    'memory/inventory_memory.csv',  # Dummy path - will use Django
                    'clean_data/cleaned_inventory.csv'  # Fallback path
                )
            else:
                # Original CSV-based initialization
                self.logger.log_process("SYSTEM", "CSV_MODE", "Initializing with CSV files")
                
                # Load mapping data
                self.mapping_df = self.memory_manager.load_csv_with_fallback(
                    Config.MEMORY_MAPPING_PATH, Config.MASTER_MAPPING_PATH
                )
                
                # Load combo data
                combo_df = self.memory_manager.load_csv_with_fallback(
                    Config.MEMORY_COMBOS_PATH, Config.MASTER_COMBOS_PATH
                )
                
                # Load inventory data
                inventory_df = self.memory_manager.load_csv_with_fallback(
                    Config.MEMORY_INVENTORY_PATH, Config.MASTER_INVENTORY_PATH
                )
            
            # Common initialization for both modes
            self.mapping_df = self.validator.normalize_column_names(self.mapping_df)
            self.combo_handler = ComboHandler(self.logger, combo_df)
            self.inventory_manager = InventoryManager(self.logger, inventory_df)
            
            # Build SKU hashtable
            self._build_sku_hashtable()
            
            mode = "Django" if self.use_django else "CSV"
            self.logger.log_process("SYSTEM", "INITIALIZED", f"All components loaded successfully ({mode} mode)")
            
        except Exception as e:
            self.logger.log_process("SYSTEM", "ERROR", f"Failed to initialize system: {str(e)}")
            raise
    
    def _build_sku_hashtable(self):
        """Build hashtable for fast SKU lookups"""
        try:
            if self.mapping_df is not None and not self.mapping_df.empty:
                # Create composite key mapping: sku|marketplace -> msku
                self._sku_hashtable = {}
                
                for _, row in self.mapping_df.iterrows():
                    sku = str(row['sku'])
                    msku = str(row['msku'])
                    panels = str(row.get('panels', ''))
                    
                    # Primary key: sku|marketplace
                    if panels:
                        composite_key = f"{sku}|{panels}"
                        self._sku_hashtable[composite_key] = msku
                    
                    # Fallback key: sku only
                    self._sku_hashtable[sku] = msku
                
                self.logger.log_process("MAPPER", "HASHTABLE", f"Built hashtable with {len(self._sku_hashtable)} mappings")
        except Exception as e:
            self.logger.log_process("MAPPER", "ERROR", f"Failed to build hashtable: {str(e)}")
            self._sku_hashtable = {}
    
    def map_sku(self, sku: str, marketplace: str = None) -> str:
        """Map individual SKU to MSKU with marketplace context"""
        try:
            if not self._sku_hashtable:
                return None
            
            # Try composite key first (sku|marketplace)
            if marketplace:
                composite_key = f"{sku}|{marketplace}"
                if composite_key in self._sku_hashtable:
                    return self._sku_hashtable[composite_key]
            
            # Fallback to SKU only
            return self._sku_hashtable.get(sku)
            
        except Exception as e:
            self.logger.log_process("MAPPER", "ERROR", f"Failed to map SKU {sku}: {str(e)}")
            return None
    
    def map_sku_with_combo_check(self, sku: str, marketplace: str = None) -> str:
        """Map SKU to MSKU, handling combo SKUs"""
        try:
            if self.combo_handler and self.combo_handler.is_combo_sku(sku):
                regular_skus = self.combo_handler.process_combo_sku(sku)
                
                if isinstance(regular_skus, list):
                    # Get MSKUs for all combo items
                    mskus = [self.map_sku(s, marketplace) for s in regular_skus if s is not None]
                    return mskus[0] if mskus else None
                else:
                    return self.map_sku(regular_skus, marketplace) if regular_skus else None
            else:
                return self.map_sku(sku, marketplace)
                
        except Exception as e:
            self.logger.log_process("MAPPER", "ERROR", f"Failed to map SKU {sku}: {str(e)}")
            return None
    
    #
    def process_sku_mappings(self, marketplace_filter: str = None):
        """Process entire dataframe and map all SKUs"""
        try:
            self.logger.log_process("MAPPER", "STARTED", f"Processing SKU mappings (marketplace: {marketplace_filter})")
            
            # Normalize column names
            self.report_data_df = self.validator.normalize_column_names(self.report_data_df)
            
            # Check if MSKU column already exists with valid data
            has_msku = 'msku' in self.report_data_df.columns
            has_msku_data = has_msku and not self.report_data_df['msku'].isnull().all()
            
            if has_msku_data:
                self.logger.log_process("MAPPER", "MSKU_EXISTS", 
                                    f"MSKU column found with data, skipping SKU mapping")
                
                # Filter by marketplace if specified
                if marketplace_filter:
                    marketplace_col = self._get_marketplace_column()
                    if marketplace_col and marketplace_col in self.report_data_df.columns:
                        original_count = len(self.report_data_df)
                        self.report_data_df = self.report_data_df[
                            self.report_data_df[marketplace_col].str.upper() == marketplace_filter.upper()
                        ]
                        filtered_count = len(self.report_data_df)
                        self.logger.log_process("MAPPER", "FILTERED", 
                                            f"Filtered by marketplace {marketplace_filter}: {original_count} → {filtered_count}")
                
                # Use existing MSKU data
                self.processed_df = self.report_data_df.dropna(subset=['msku'])
                
                # Check for any missing MSKUs
                missing_msku_count = len(self.report_data_df[self.report_data_df['msku'].isnull()])
                if missing_msku_count > 0:
                    self.logger.log_process("MAPPER", "MISSING_MSKU", 
                                        f"Found {missing_msku_count} records with missing MSKU")
                
                self.logger.log_process("MAPPER", "COMPLETED", f"Processed {len(self.processed_df)} records")
                return
            
            # If no MSKU data, validate SKU column exists for mapping
            is_valid, error_msg = self.validator.validate_required_columns(self.report_data_df, ['sku'])
            if not is_valid:
                self.logger.log_process("MAPPER", "ERROR", f"Validation failed: {error_msg}")
                return
            
            # Filter by marketplace if specified
            if marketplace_filter:
                marketplace_col = self._get_marketplace_column()
                if marketplace_col and marketplace_col in self.report_data_df.columns:
                    original_count = len(self.report_data_df)
                    self.report_data_df = self.report_data_df[
                        self.report_data_df[marketplace_col].str.upper() == marketplace_filter.upper()
                    ]
                    filtered_count = len(self.report_data_df)
                    self.logger.log_process("MAPPER", "FILTERED", 
                                        f"Filtered by marketplace {marketplace_filter}: {original_count} → {filtered_count}")
            
            # Map SKUs to MSKUs
            marketplace_col = self._get_marketplace_column()
            
            if marketplace_col and marketplace_col in self.report_data_df.columns:
                # Use marketplace context for mapping
                self.report_data_df['msku'] = self.report_data_df.apply(
                    lambda row: self.map_sku_with_combo_check(row['sku'], row[marketplace_col]), axis=1
                )
            else:
                # Map without marketplace context
                self.report_data_df['msku'] = self.report_data_df['sku'].apply(
                    lambda sku: self.map_sku_with_combo_check(sku, marketplace_filter)
                )
            
            # Identify unmapped SKUs
            self.unmapped_skus = self.report_data_df[self.report_data_df['msku'].isnull()]['sku'].unique().tolist()
            
            if self.unmapped_skus:
                self.logger.log_process("MAPPER", "UNMAPPED", f"Found {len(self.unmapped_skus)} unmapped SKUs")
            
            # Save processed data
            self.processed_df = self.report_data_df.dropna(subset=['msku'])
            
            self.logger.log_process("MAPPER", "COMPLETED", f"Processed {len(self.processed_df)} records")
            
        except Exception as e:
            self.logger.log_process("MAPPER", "ERROR", f"Failed to process mappings: {str(e)}")
           
        self.logger.log_process("MAPPER", "DEBUG", f"Full error: {traceback.format_exc()}")

    def _get_marketplace_column(self) -> str:
        """Get the marketplace column name from the dataframe"""
        marketplace_columns = ['panels', 'panel', 'marketplace', 'source']
        for col in marketplace_columns:
            if col in self.report_data_df.columns:
                return col
        return None
    
    def update_inventory(self):
        """Update inventory with processed orders"""
        try:
            if self.processed_df is None or self.processed_df.empty:
                self.logger.log_process("INVENTORY", "ERROR", "No processed data for inventory update")
                return
            
            if self.use_django:
                # NEW: Django-based inventory updates
                self._update_inventory_django()
            else:
                # Original CSV-based inventory update
                if self.inventory_manager:
                    self.processed_df = self.inventory_manager.update_inventory_with_orders(self.processed_df)
            
            self.logger.log_process("INVENTORY", "UPDATED", "Inventory updated successfully")
            
        except Exception as e:
            self.logger.log_process("INVENTORY", "ERROR", f"Failed to update inventory: {str(e)}")
    
    def _update_inventory_django(self):
        """Update inventory using Django models"""
        try:
            for _, row in self.processed_df.iterrows():
                try:
                    msku = row['msku']
                    quantity = int(row['quantity'])
                    warehouse_code = row.get('warehouse', Config.DEFAULT_WAREHOUSE)
                    
                    # Update stock in Django
                    success = self.memory_manager.update_inventory_stock(
                        msku=msku,
                        warehouse_code=warehouse_code,
                        quantity_change=-quantity,  # Negative for outbound
                        movement_type='OUTBOUND',
                        reference="Web app order"
                    )
                    
                    if success:
                        # Update the processed dataframe
                        self.processed_df.at[row.name, 'warehouse'] = warehouse_code
                
                except Exception as row_error:
                    self.logger.log_process("INVENTORY", "ROW_ERROR", 
                                          f"Failed to update inventory for row: {str(row_error)}")
                    continue
            
        except Exception as e:
            self.logger.log_process("INVENTORY", "ERROR", f"Failed to update Django inventory: {str(e)}")
    
    def get_outbound_data(self, marketplace) -> pd.DataFrame:
        """Get formatted outbound data"""
        return self.output_processor.format_outbound_data(self.processed_df, marketplace)
    
    def load_additional_mappings(self, mapping_file_path: str, replace_existing: bool = False):
        """Load additional mapping data"""
        try:
            self.mapping_df = self.memory_manager.load_mapping_data(mapping_file_path, replace_existing)
            self._build_sku_hashtable()
            self.logger.log_process("MAPPER", "MAPPINGS_LOADED", f"Additional mappings loaded from {mapping_file_path}")
            
        except Exception as e:
            self.logger.log_process("MAPPER", "ERROR", f"Failed to load additional mappings: {str(e)}")
    
    def get_processing_summary(self) -> dict:
        """Get summary of processing results"""
        return {
            'total_rows_processed': len(self.processed_df) if self.processed_df is not None else 0,
            'unmapped_skus_count': len(self.unmapped_skus),
            'unmapped_skus': self.unmapped_skus[:10],  # First 10 for display
            'success_rate': (len(self.processed_df) / len(self.report_data_df) * 100) if self.processed_df is not None and len(self.report_data_df) > 0 else 0,
            'data_type': self.data_type,
            'use_django': self.use_django
        }