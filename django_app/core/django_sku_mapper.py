from sku_mapper.core.mapper import SKUMapper
from sku_mapper.core.logger import WMSLogger
from sku_mapper.core.data_validator import DataValidator
from .services.baserow_memory_manager import DjangoMemoryManager
from sku_mapper.core.combo_handler import ComboHandler
from sku_mapper.core.inventory_manager import InventoryManager
from sku_mapper.processors.output_processor import OutputProcessor
import pandas as pd

class DjangoSKUMapper(SKUMapper):
    """
    Modified SKU_Mapper that uses Django models instead of CSV files
    Drop-in replacement for your original SKU_Mapper
    """
    
    def __init__(self, report_data_df: pd.DataFrame, data_type: str = 'outbound'):
        """Initialize with Django-backed memory management"""
        self.report_data_df = report_data_df.copy()
        self.data_type = data_type
        
        # Initialize components with Django memory manager
        self.logger = WMSLogger()
        self.validator = DataValidator(self.logger)
        self.memory_manager = DjangoMemoryManager(self.logger, self.validator)  # ← Django-backed!
        self.output_processor = OutputProcessor(self.logger)
        
        # Data attributes
        self.mapping_df = None
        self.combo_handler = None
        self.inventory_manager = None
        self.processed_df = None
        self.unmapped_skus = []
        
        # SKU mapping hashtable
        self._sku_hashtable = None
        
        # Initialize system (now Django-backed)
        self._initialize_system()
    
    def _initialize_system(self):
        """Initialize system with Django models backing the CSV memory"""
        try:
            # Ensure fresh data from Django models
            self.sync_with_django()
            
            # Load mapping data (now from Django-backed memory)
            self.mapping_df = self.memory_manager.load_mapping_data()
            self.mapping_df = self.validator.normalize_column_names(self.mapping_df)
            
            # Load combo data (from Django-backed memory)
            from pathlib import Path
            combo_memory_path = Path('memory/combo_sku_memory.csv')
            combo_master_path = Path('clean_data/combo_sku_clean.csv')
            
            combo_df = self.memory_manager.load_csv_with_fallback(
                combo_memory_path, combo_master_path
            )
            self.combo_handler = ComboHandler(self.logger, combo_df)
            
            # Load inventory data (from Django-backed memory)
            inventory_memory_path = Path('memory/inventory_memory.csv')
            inventory_master_path = Path('clean_data/cleaned_inventory.csv')
            
            inventory_df = self.memory_manager.load_csv_with_fallback(
                inventory_memory_path, inventory_master_path
            )
            self.inventory_manager = InventoryManager(self.logger, inventory_df)
            
            # Build SKU hashtable
            self._build_sku_hashtable()
            
            self.logger.log_process("SYSTEM", "INITIALIZED", "Django-backed system loaded successfully")
            
        except Exception as e:
            self.logger.log_process("SYSTEM", "ERROR", f"Failed to initialize Django system: {str(e)}")
            raise
    
    def sync_with_django(self):
        """Sync Django models to memory CSV files before processing"""
        try:
            self.logger.log_process("DJANGO", "SYNC", "Syncing Django models to memory files...")
            
            # Export fresh data from Django models to memory CSV
            export_results = self.memory_manager.baserow_manager.export_django_to_memory_csv()
            
            if all(export_results.values()):
                self.logger.log_process("DJANGO", "SUCCESS", "Django sync completed")
            else:
                self.logger.log_process("DJANGO", "WARNING", "Some Django sync operations failed")
                
        except Exception as e:
            self.logger.log_process("DJANGO", "ERROR", f"Django sync failed: {str(e)}")
    
    def sync_with_baserow(self):
        """Full sync with Baserow (push Django → Baserow → pull → CSV)"""
        try:
            self.logger.log_process("BASEROW", "SYNC", "Starting full Baserow sync...")
            
            results = self.memory_manager.baserow_manager.full_sync_process()
            
            if results['success']:
                self.logger.log_process("BASEROW", "SUCCESS", "Baserow sync completed")
                # Reload data after sync
                self._initialize_system()
            else:
                self.logger.log_process("BASEROW", "ERROR", "Baserow sync failed")
                
            return results
            
        except Exception as e:
            self.logger.log_process("BASEROW", "ERROR", f"Baserow sync failed: {str(e)}")
            return {'success': False, 'error': str(e)}