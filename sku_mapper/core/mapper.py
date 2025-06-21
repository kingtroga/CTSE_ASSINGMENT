import pandas as pd
from ..utils.constants import Config
from .logger import WMSLogger
from .data_validator import DataValidator
from .memory_manager import MemoryManager
from .combo_handler import ComboHandler
from .inventory_manager import InventoryManager
from ..processors.output_processor import OutputProcessor

class SKUMapper:
    """Main SKU Mapper class - orchestrates all operations"""
    
    def __init__(self, report_data_df: pd.DataFrame, data_type: str = 'outbound'):
        """Initialize SKU Mapper with report data"""
        self.report_data_df = report_data_df.copy()
        self.data_type = data_type
        
        # Initialize components
        self.logger = WMSLogger()
        self.validator = DataValidator(self.logger)
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
            # Load mapping data
            self.mapping_df = self.memory_manager.load_csv_with_fallback(
                Config.MEMORY_MAPPING_PATH, Config.MASTER_MAPPING_PATH
            )
            self.mapping_df = self.validator.normalize_column_names(self.mapping_df)
            
            # Load combo data
            combo_df = self.memory_manager.load_csv_with_fallback(
                Config.MEMORY_COMBOS_PATH, Config.MASTER_COMBOS_PATH
            )
            self.combo_handler = ComboHandler(self.logger, combo_df)
            
            # Load inventory data
            inventory_df = self.memory_manager.load_csv_with_fallback(
                Config.MEMORY_INVENTORY_PATH, Config.MASTER_INVENTORY_PATH
            )
            self.inventory_manager = InventoryManager(self.logger, inventory_df)
            
            # Build SKU hashtable
            self._build_sku_hashtable()
            
            self.logger.log_process("SYSTEM", "INITIALIZED", "All components loaded successfully")
            
        except Exception as e:
            self.logger.log_process("SYSTEM", "ERROR", f"Failed to initialize system: {str(e)}")
            raise
    
    def _build_sku_hashtable(self):
        """Build hashtable for fast SKU lookups"""
        try:
            if self.mapping_df is not None and not self.mapping_df.empty:
                self._sku_hashtable = dict(zip(self.mapping_df['sku'], self.mapping_df['msku']))
                self.logger.log_process("MAPPER", "HASHTABLE", f"Built hashtable with {len(self._sku_hashtable)} mappings")
        except Exception as e:
            self.logger.log_process("MAPPER", "ERROR", f"Failed to build hashtable: {str(e)}")
            self._sku_hashtable = {}
    
    def map_sku(self, sku: str) -> str:
        """Map individual SKU to MSKU"""
        try:
            return self._sku_hashtable.get(sku) if self._sku_hashtable else None
        except:
            return None
    
    def map_sku_with_combo_check(self, sku: str) -> str:
        """Map SKU to MSKU, handling combo SKUs"""
        try:
            if self.combo_handler and self.combo_handler.is_combo_sku(sku):
                regular_skus = self.combo_handler.process_combo_sku(sku)
                
                if isinstance(regular_skus, list):
                    mskus = [self.map_sku(s) for s in regular_skus if s is not None]
                    return mskus[0] if mskus else None
                else:
                    return self.map_sku(regular_skus) if regular_skus else None
            else:
                return self.map_sku(sku)
                
        except Exception as e:
            self.logger.log_process("MAPPER", "ERROR", f"Failed to map SKU {sku}: {str(e)}")
            return None
    
    def process_sku_mappings(self):
        """Process entire dataframe and map all SKUs"""
        try:
            self.logger.log_process("MAPPER", "STARTED", "Processing SKU mappings")
            
            # Normalize column names
            self.report_data_df = self.validator.normalize_column_names(self.report_data_df)
            
            # Validate required columns
            is_valid, error_msg = self.validator.validate_required_columns(self.report_data_df, ['sku'])
            if not is_valid:
                self.logger.log_process("MAPPER", "ERROR", f"Validation failed: {error_msg}")
                return
            
            # Map SKUs to MSKUs if column doesn't exist or is empty
            if 'msku' not in self.report_data_df.columns or self.report_data_df['msku'].isnull().all():
                self.report_data_df['msku'] = self.report_data_df['sku'].apply(self.map_sku_with_combo_check)
            
            # Identify unmapped SKUs
            self.unmapped_skus = self.report_data_df[self.report_data_df['msku'].isnull()]['sku'].unique().tolist()
            
            if self.unmapped_skus:
                self.logger.log_process("MAPPER", "UNMAPPED", f"Found {len(self.unmapped_skus)} unmapped SKUs")
            
            # Save processed data
            self.processed_df = self.report_data_df.dropna(subset=['msku'])
            
            self.logger.log_process("MAPPER", "COMPLETED", f"Processed {len(self.processed_df)} records")
            
        except Exception as e:
            self.logger.log_process("MAPPER", "ERROR", f"Failed to process mappings: {str(e)}")
    
    def update_inventory(self):
        """Update inventory with processed orders"""
        try:
            if self.processed_df is None or self.processed_df.empty:
                self.logger.log_process("INVENTORY", "ERROR", "No processed data for inventory update")
                return
            
            if self.inventory_manager:
                self.processed_df = self.inventory_manager.update_inventory_with_orders(self.processed_df)
                self.logger.log_process("INVENTORY", "UPDATED", "Inventory updated successfully")
            
        except Exception as e:
            self.logger.log_process("INVENTORY", "ERROR", f"Failed to update inventory: {str(e)}")
    
    def get_outbound_data(self) -> pd.DataFrame:
        """Get formatted outbound data"""
        return self.output_processor.format_outbound_data(self.processed_df)
    
    def load_additional_mappings(self, mapping_file_path: str, replace_existing: bool = False):
        """Load additional mapping data"""
        try:
            self.mapping_df = self.memory_manager.load_mapping_data(mapping_file_path, replace_existing)
            self._build_sku_hashtable()
            self.logger.log_process("MAPPER", "MAPPINGS_LOADED", f"Additional mappings loaded from {mapping_file_path}")
            
        except Exception as e:
            self.logger.log_process("MAPPER", "ERROR", f"Failed to load additional mappings: {str(e)}")