# Project Structure:
# sku_mapper/
# ├── __init__.py
# ├── core/
# │   ├── __init__.py
# │   ├── mapper.py          # Main SKU_Mapper class (orchestrator)
# │   ├── memory_manager.py  # Memory/file operations
# │   ├── data_validator.py  # Validation & normalization
# │   ├── combo_handler.py   # Combo product logic
# │   ├── inventory_manager.py # Inventory operations
# │   └── logger.py          # Logging system
# ├── utils/
# │   ├── __init__.py
# │   └── constants.py       # Constants and configurations
# └── processors/
#     ├── __init__.py
#     ├── input_processor.py  # Input data processing
#     └── output_processor.py # Output formatting

# =============================================================================
# File: sku_mapper/utils/constants.py
# =============================================================================

from pathlib import Path

class Config:
    """Configuration constants for SKU Mapper system"""
    
    # Directory paths
    MEMORY_DIR = Path('memory')
    LOGS_DIR = Path('logs') 
    CLEAN_DATA_DIR = Path('clean_data')
    RAW_REPORTS_DIR = Path('raw_daily_reports')
    
    # Memory file paths
    MEMORY_COMBOS_PATH = MEMORY_DIR / 'combo_sku_memory.csv'
    MEMORY_INVENTORY_PATH = MEMORY_DIR / 'inventory_memory.csv'
    MEMORY_MAPPING_PATH = MEMORY_DIR / 'sku_mappings_memory.csv'
    
    # Master file paths
    MASTER_COMBOS_PATH = CLEAN_DATA_DIR / 'combo_sku_clean.csv'
    MASTER_INVENTORY_PATH = CLEAN_DATA_DIR / 'cleaned_inventory.csv'
    MASTER_MAPPING_PATH = CLEAN_DATA_DIR / 'sku_mappings_final_clean.csv'
    
    # Warehouse codes
    WAREHOUSE_COLUMNS = ['TLCQ', 'BLR7', 'BLR8', 'BOM5', 'BOM7', 'CCU1', 'CCX1', 
                        'DEL4', 'DEL5', 'DEX3', 'PNQ2', 'PNQ3', 'SDED', 'SDEE', 'XHJ9']
    
    # Default values
    DEFAULT_WAREHOUSE = 'TLCQ'
    
    # Column mappings for normalization
    COLUMN_MAPPINGS = {
        # SKU variations
        'SKU': 'sku', 'Sku': 'sku', 'sKu': 'sku', 'skU': 'sku',
        'SKU_ID': 'sku', 'sku_id': 'sku', 'Sku_Id': 'sku',
        'product_sku': 'sku', 'Product_SKU': 'sku',
        
        # MSKU variations
        'MSKU': 'msku', 'Msku': 'msku', 'mSku': 'msku', 'mskU': 'msku',
        'MASTER_SKU': 'msku', 'master_sku': 'msku', 'Master_Sku': 'msku',
        'parent_sku': 'msku', 'Parent_SKU': 'msku',
        
        # Panel/Marketplace variations
        'PANELS': 'panels', 'Panels': 'panels', 'PANEL': 'panels', 'Panel': 'panels',
        'panels': 'panels', 'panel': 'panels',
        'marketplace': 'panels', 'Marketplace': 'panels', 'MARKETPLACE': 'panels',
        'source': 'panels', 'Source': 'panels', 'SOURCE': 'panels',
        
        # Other common variations
        'DATE': 'date', 'Date': 'date',
        'QUANTITY': 'quantity', 'Quantity': 'quantity', 'qty': 'quantity', 'QTY': 'quantity',
        'WAREHOUSE': 'warehouse', 'Warehouse': 'warehouse', 'wh': 'warehouse', 'WH': 'warehouse'
    }

# =============================================================================
# File: sku_mapper/core/logger.py
# =============================================================================

import logging
from pathlib import Path
from ..utils.constants import Config

class WMSLogger:
    """Centralized logging system for WMS operations"""
    
    def __init__(self):
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Setup logging for mapping process"""
        # Create logs directory
        Config.LOGS_DIR.mkdir(exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(Config.LOGS_DIR / 'sku_mapping.log'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def log_process(self, component: str, action: str, message: str):
        """Log process with structured format"""
        log_message = f"{component} | {action} | {message}"
        self.logger.info(log_message)
        print(log_message)  # Also print to console

# =============================================================================
# File: sku_mapper/core/data_validator.py
# =============================================================================

import pandas as pd
from ..utils.constants import Config
from .logger import WMSLogger

class DataValidator:
    """Handles data validation and normalization"""
    
    def __init__(self, logger: WMSLogger):
        self.logger = logger
    
    def normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to standard format"""
        try:
            # Apply column mapping
            df_normalized = df.rename(columns=Config.COLUMN_MAPPINGS)
            
            # Convert all column names to lowercase as fallback
            df_normalized.columns = df_normalized.columns.str.lower().str.strip()
            
            self.logger.log_process("VALIDATOR", "SUCCESS", f"Normalized columns: {list(df_normalized.columns)}")
            return df_normalized
            
        except Exception as e:
            self.logger.log_process("VALIDATOR", "ERROR", f"Failed to normalize columns: {str(e)}")
            return df
    
    def validate_required_columns(self, df: pd.DataFrame, required_columns: list) -> tuple:
        """Validate that required columns exist in the dataframe"""
        try:
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                available_columns = list(df.columns)
                error_msg = f"Missing required columns: {missing_columns}. Available: {available_columns}"
                return False, error_msg
            
            return True, "All required columns present"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def clean_dataframe(self, df: pd.DataFrame, required_columns: list) -> pd.DataFrame:
        """Clean dataframe by removing duplicates and null values"""
        try:
            # Remove duplicates based on composite key
            if len(required_columns) > 1:
                df_clean = df.drop_duplicates(required_columns[:2])  # Use first 2 columns as key
            else:
                df_clean = df.drop_duplicates()
            
            # Remove rows with null values in required columns
            df_clean = df_clean.dropna(subset=required_columns)
            
            self.logger.log_process("VALIDATOR", "CLEANED", f"Cleaned data: {len(df_clean)} records")
            return df_clean
            
        except Exception as e:
            self.logger.log_process("VALIDATOR", "ERROR", f"Failed to clean dataframe: {str(e)}")
            return df

# =============================================================================
# File: sku_mapper/core/memory_manager.py
# =============================================================================

import pandas as pd
from pathlib import Path
from ..utils.constants import Config
from .logger import WMSLogger
from .data_validator import DataValidator

class MemoryManager:
    """Manages file operations and memory caching"""
    
    def __init__(self, logger: WMSLogger, validator: DataValidator):
        self.logger = logger
        self.validator = validator
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories"""
        Config.MEMORY_DIR.mkdir(exist_ok=True)
        Config.LOGS_DIR.mkdir(exist_ok=True)
    
    def is_valid_csv(self, file_path: Path) -> bool:
        """Check if CSV file exists and has valid data"""
        try:
            if not file_path.exists():
                return False
            
            df = pd.read_csv(file_path)
            return not df.empty and len(df.columns) > 0
            
        except (pd.errors.EmptyDataError, pd.errors.ParserError, FileNotFoundError):
            return False
        except Exception:
            return False
    
    def load_csv_with_fallback(self, memory_path: Path, master_path: Path) -> pd.DataFrame:
        """Load CSV from memory with fallback to master file"""
        try:
            if self.is_valid_csv(memory_path):
                df = pd.read_csv(memory_path)
                self.logger.log_process("MEMORY", "LOADED", f"Data loaded from memory: {memory_path}")
                return df
            else:
                df = pd.read_csv(master_path)
                self.logger.log_process("MEMORY", "LOADED", f"Data loaded from master: {master_path}")
                return df
                
        except Exception as e:
            self.logger.log_process("MEMORY", "ERROR", f"Failed to load data: {str(e)}")
            raise
    
    def save_to_memory(self, df: pd.DataFrame, memory_path: Path) -> bool:
        """Save dataframe to memory"""
        try:
            if df is not None and not df.empty:
                df.to_csv(memory_path, index=False)
                self.logger.log_process("MEMORY", "SAVED", f"Data saved to: {memory_path}")
                return True
            else:
                self.logger.log_process("MEMORY", "ERROR", "Cannot save empty dataframe")
                return False
                
        except Exception as e:
            self.logger.log_process("MEMORY", "ERROR", f"Failed to save data: {str(e)}")
            return False
    
    def load_mapping_data(self, additional_mapping_path: str = None, replace_existing: bool = False) -> pd.DataFrame:
        """Load mapping data with option to add additional mappings"""
        try:
            # Load base mapping data
            base_mapping = self.load_csv_with_fallback(
                Config.MEMORY_MAPPING_PATH, 
                Config.MASTER_MAPPING_PATH
            )
            
            # Normalize base mapping
            base_mapping = self.validator.normalize_column_names(base_mapping)
            
            if additional_mapping_path and Path(additional_mapping_path).exists():
                additional_mapping = pd.read_csv(additional_mapping_path)
                additional_mapping = self.validator.normalize_column_names(additional_mapping)
                
                # Validate required columns
                is_valid, error_msg = self.validator.validate_required_columns(
                    additional_mapping, ['sku', 'msku', 'panels']
                )
                
                if not is_valid:
                    self.logger.log_process("MEMORY", "ERROR", f"Additional mapping validation failed: {error_msg}")
                    return base_mapping
                
                # Clean additional mapping
                additional_mapping = self.validator.clean_dataframe(
                    additional_mapping, ['sku', 'panels']
                )
                
                if replace_existing:
                    final_mapping = additional_mapping
                    self.logger.log_process("MEMORY", "REPLACED", "Mapping data replaced")
                else:
                    final_mapping = pd.concat([base_mapping, additional_mapping]).drop_duplicates(['sku', 'panels'])
                    self.logger.log_process("MEMORY", "MERGED", "Additional mapping data merged")
                
                # Save updated mapping
                self.save_to_memory(final_mapping, Config.MEMORY_MAPPING_PATH)
                return final_mapping
            
            return base_mapping
            
        except Exception as e:
            self.logger.log_process("MEMORY", "ERROR", f"Failed to load mapping data: {str(e)}")
            raise

# =============================================================================
# File: sku_mapper/core/combo_handler.py
# =============================================================================

import pandas as pd
from ..utils.constants import Config
from .logger import WMSLogger

class ComboHandler:
    """Handles combo product operations"""
    
    def __init__(self, logger: WMSLogger, combo_df: pd.DataFrame):
        self.logger = logger
        self.combo_df = combo_df
        self._combo_hashtable = None
        self._build_combo_hashtable()
    
    def _build_combo_hashtable(self):
        """Build hashtable for combo SKU lookups"""
        try:
            self._combo_hashtable = {}
            
            if self.combo_df is not None and not self.combo_df.empty:
                combo_skus = self.combo_df['Combo'].dropna()
                combo_skus = combo_skus[combo_skus != 'NA']
                
                for combo_sku in combo_skus:
                    self._combo_hashtable[combo_sku] = True
                    
                self.logger.log_process("COMBO", "INITIALIZED", f"Combo hashtable built with {len(self._combo_hashtable)} entries")
            
        except Exception as e:
            self.logger.log_process("COMBO", "ERROR", f"Failed to build combo hashtable: {str(e)}")
            self._combo_hashtable = {}
    
    def is_combo_sku(self, sku: str) -> bool:
        """Check if SKU is a combo SKU"""
        try:
            return self._combo_hashtable.get(sku, False) if self._combo_hashtable else False
        except:
            return False
    
    def process_combo_sku(self, combo_sku: str) -> list:
        """Get regular SKUs associated with a combo SKU"""
        try:
            combo_row = self.combo_df[self.combo_df['Combo'] == combo_sku]
            
            if combo_row.empty:
                return []
            
            # Get all SKU columns (SKU1, SKU2, SKU3, etc.)
            sku_columns = [col for col in self.combo_df.columns if col.startswith('SKU')]
            
            regular_skus = []
            for col in sku_columns:
                sku_value = combo_row[col].iloc[0]
                if sku_value is not None and str(sku_value) not in ['nan', 'NA', '']:
                    regular_skus.append(sku_value)
            
            self.logger.log_process("COMBO", "PROCESSED", f"Combo {combo_sku} → {regular_skus}")
            return regular_skus if len(regular_skus) > 1 else (regular_skus[0] if regular_skus else None)
            
        except Exception as e:
            self.logger.log_process("COMBO", "ERROR", f"Failed to process combo SKU {combo_sku}: {str(e)}")
            return []

# =============================================================================
# File: sku_mapper/core/inventory_manager.py
# =============================================================================

import pandas as pd
from datetime import datetime
from ..utils.constants import Config
from .logger import WMSLogger

class InventoryManager:
    """Manages inventory operations and warehouse assignments"""
    
    def __init__(self, logger: WMSLogger, inventory_df: pd.DataFrame):
        self.logger = logger
        self.inventory_df = inventory_df.copy() if inventory_df is not None else None
    
    def update_inventory_with_orders(self, processed_orders: pd.DataFrame) -> pd.DataFrame:
        """Update inventory with order quantities and assign warehouses"""
        try:
            if self.inventory_df is None or self.inventory_df.empty:
                self.logger.log_process("INVENTORY", "ERROR", "Inventory DataFrame is empty")
                return processed_orders
            
            updated_inventory = self.inventory_df.copy()
            updated_orders = processed_orders.copy()
            
            # Add warehouse column if missing
            if 'warehouse' not in updated_orders.columns:
                updated_orders['warehouse'] = Config.DEFAULT_WAREHOUSE
            
            # Add last_updated column to inventory
            updated_inventory['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Process each order
            for idx in range(len(updated_orders)):
                try:
                    msku = updated_orders.iloc[idx]['msku']
                    quantity = updated_orders.iloc[idx]['quantity']
                    
                    warehouse = self._assign_warehouse_for_order(updated_inventory, msku, quantity)
                    updated_orders.at[updated_orders.index[idx], 'warehouse'] = warehouse
                    
                    # Update inventory
                    self._update_stock_for_msku(updated_inventory, msku, quantity, warehouse)
                    
                except Exception as order_error:
                    self.logger.log_process("INVENTORY", "ORDER_ERROR", 
                                          f"Failed to process order {idx}: {str(order_error)}")
                    continue
            
            # Save updated inventory
            from .memory_manager import MemoryManager
            # Note: This creates a circular dependency - needs refactoring
            # For now, save directly
            updated_inventory.to_csv(Config.MEMORY_INVENTORY_PATH, index=False)
            self.inventory_df = updated_inventory
            
            self.logger.log_process("INVENTORY", "UPDATED", 
                                  f"Processed {len(updated_orders)} orders")
            
            return updated_orders
            
        except Exception as e:
            self.logger.log_process("INVENTORY", "ERROR", f"Failed to update inventory: {str(e)}")
            return processed_orders
    
    def _assign_warehouse_for_order(self, inventory_df: pd.DataFrame, msku: str, quantity: int) -> str:
        """Assign optimal warehouse for an order"""
        try:
            inventory_matches = inventory_df[inventory_df['msku'] == msku]
            
            if inventory_matches.empty:
                self.logger.log_process("INVENTORY", "NOT_FOUND", f"MSKU {msku} not in inventory")
                return 'NOT_FOUND'
            
            product_idx = inventory_matches.index[0]
            
            # Find warehouse with sufficient stock
            warehouse_stocks = {}
            for wh in Config.WAREHOUSE_COLUMNS:
                if wh in inventory_df.columns:
                    stock = inventory_df.at[product_idx, wh]
                    if pd.notna(stock) and stock >= quantity:
                        warehouse_stocks[wh] = stock
            
            if warehouse_stocks:
                # Select warehouse with highest stock
                best_warehouse = max(warehouse_stocks, key=warehouse_stocks.get)
                self.logger.log_process("INVENTORY", "ASSIGNED", 
                                      f"MSKU {msku}: {quantity} units from {best_warehouse}")
                return best_warehouse
            else:
                # No sufficient stock - use backtrack logic
                best_warehouse = self._find_best_warehouse_for_backtrack(inventory_df, product_idx)
                self.logger.log_process("INVENTORY", "BACKTRACK", 
                                      f"MSKU {msku}: {quantity} units from {best_warehouse} (insufficient stock)")
                return best_warehouse
                
        except Exception as e:
            self.logger.log_process("INVENTORY", "ERROR", f"Failed to assign warehouse for {msku}: {str(e)}")
            return Config.DEFAULT_WAREHOUSE
    
    def _find_best_warehouse_for_backtrack(self, inventory_df: pd.DataFrame, product_idx: int) -> str:
        """Find best warehouse when no sufficient stock available"""
        best_warehouse = Config.DEFAULT_WAREHOUSE
        best_stock = float('-inf')
        
        for wh in Config.WAREHOUSE_COLUMNS:
            if wh in inventory_df.columns:
                stock = inventory_df.at[product_idx, wh]
                if pd.notna(stock) and stock > best_stock:
                    best_stock = stock
                    best_warehouse = wh
        
        return best_warehouse
    
    def _update_stock_for_msku(self, inventory_df: pd.DataFrame, msku: str, quantity: int, warehouse: str):
        """Update stock for specific MSKU in warehouse"""
        try:
            inventory_matches = inventory_df[inventory_df['msku'] == msku]
            
            if not inventory_matches.empty and warehouse in inventory_df.columns:
                product_idx = inventory_matches.index[0]
                current_stock = inventory_df.at[product_idx, warehouse]
                
                if pd.notna(current_stock):
                    inventory_df.at[product_idx, warehouse] = current_stock - quantity
                    inventory_df.at[product_idx, 'last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    self.logger.log_process("INVENTORY", "STOCK_UPDATED", 
                                          f"MSKU {msku}: -{quantity} from {warehouse} (new stock: {current_stock - quantity})")
                
        except Exception as e:
            self.logger.log_process("INVENTORY", "ERROR", f"Failed to update stock for {msku}: {str(e)}")

# =============================================================================
# File: sku_mapper/processors/output_processor.py
# =============================================================================

import pandas as pd
from datetime import datetime
from ..utils.constants import Config
from ..core.logger import WMSLogger

class OutputProcessor:
    """Handles output data formatting and processing"""
    
    def __init__(self, logger: WMSLogger):
        self.logger = logger
    
    def format_outbound_data(self, processed_df: pd.DataFrame) -> pd.DataFrame:
        """Format data for outbound orders: [date, panel, sku, msku, quantity, warehouse]"""
        try:
            if processed_df is None or processed_df.empty:
                self.logger.log_process("OUTPUT", "ERROR", "No processed data available")
                return None
            
            outbound_df = processed_df.copy()
            
            # Add missing columns with defaults
            if 'order date' in outbound_df.columns:
                outbound_df['date'] = outbound_df['order date']
            elif 'date' not in outbound_df.columns:
                outbound_df['date'] = datetime.now().strftime('%Y-%m-%d')
            
            if 'panels' in outbound_df.columns:
                outbound_df['panel'] = outbound_df['panels']
            elif 'panel' not in outbound_df.columns:
                outbound_df['panel'] = 'unknown'
            
            if 'warehouse' not in outbound_df.columns:
                outbound_df['warehouse'] = Config.DEFAULT_WAREHOUSE
            
            # Clean warehouse assignments
            outbound_df['warehouse'] = outbound_df['warehouse'].replace(
                ['NO_STOCK', 'NOT_FOUND'], Config.DEFAULT_WAREHOUSE
            )
            
            # Select required columns
            required_columns = ['date', 'panel', 'sku', 'msku', 'quantity', 'warehouse']
            available_columns = [col for col in required_columns if col in outbound_df.columns]
            
            if len(available_columns) < 4:  # At minimum need sku, msku, quantity
                self.logger.log_process("OUTPUT", "ERROR", f"Insufficient columns available: {available_columns}")
                return None
            
            outbound_df = outbound_df[available_columns]
            
            # Remove rows with critical missing data
            critical_columns = ['sku', 'msku', 'quantity']
            available_critical = [col for col in critical_columns if col in outbound_df.columns]
            outbound_df = outbound_df.dropna(subset=available_critical)
            
            self.logger.log_process("OUTPUT", "SUCCESS", 
                                  f"Outbound data formatted: {len(outbound_df)} records")
            
            return outbound_df
            
        except Exception as e:
            self.logger.log_process("OUTPUT", "ERROR", f"Failed to format outbound data: {str(e)}")
            return None

# =============================================================================
# File: sku_mapper/core/mapper.py
# =============================================================================

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
            if 'msku' not in self.report_data_df.columns or self.report_data_df['msku'].isnull().all():
                is_valid, error_msg = self.validator.validate_required_columns(self.report_data_df, ['sku'])
                if not is_valid:
                    self.logger.log_process("MAPPER", "ERROR", f"Validation failed: {error_msg}")
                    return
            
            # Map SKUs to MSKUs if column doesn't exist or is empty
            if 'msku' not in self.report_data_df.columns or self.report_data_df['msku'].isnull().all():
                self.report_data_df['msku'] = self.report_data_df['sku'].apply(self.map_sku_with_combo_check)
            
            # Only map if 'msku' is missing or empty AND 'sku' is available
            if 'msku' not in self.report_data_df.columns or self.report_data_df['msku'].isnull().all():
                if 'sku' in self.report_data_df.columns:
                    self.report_data_df['msku'] = self.report_data_df['sku'].apply(self.map_sku_with_combo_check)
                else:
                    self.logger.log_process("MAPPER", "ERROR", "Cannot map MSKUs: 'sku' column is missing")
                    return

            
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

# =============================================================================
# File: sku_mapper/__init__.py
# =============================================================================

from .core.mapper import SKUMapper
from .utils.constants import Config

__all__ = ['SKUMapper', 'Config']

# =============================================================================
# Usage Example
# =============================================================================

if __name__ == "__main__":
    # Example usage
    import pandas as pd
    
    # Load report data
    report_data = pd.read_csv('raw_daily_reports/rudrav_meesho/rudrav_meesho.csv')
    
    # Initialize SKU Mapper
    mapper = SKUMapper(report_data)
    
    # Process SKU mappings
    mapper.process_sku_mappings()
    
    # Update inventory
    mapper.update_inventory()
    
    # Get outbound data
    outbound_data = mapper.get_outbound_data()
    
    # Save results
    if outbound_data is not None:
        outbound_data.to_csv('outbound_orders.csv', index=False)
    
    # Print unmapped SKUs
    if mapper.unmapped_skus:
        print("Unmapped SKUs:")
        for sku in mapper.unmapped_skus:
            print(f"  - {sku}")