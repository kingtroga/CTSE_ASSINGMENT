import pandas as pd
import os
import logging
from pathlib import Path

# 1. Create a SKU Mapper Class: Develop a class for managing SKU to MSKU mappings
class SKU_Mapper:
    """
    This class is responsible for managing SKU to MSKU mappings, 
    and processing sales data to identify and map SKUs to their corresponding MSKUs

    Input: report_data_df (DataFrame):
    A DataFrame containing sales data with SKUs along with other data to be processed.
    Could be from: cste_amazon, cste_fk, cste_meesho, gl_fk, rudrav_meesho, or misc

    Output: Standardized DataFrame with columns:
    [date, panel, sku, msku, quantity, warehouse] - could be outbound or return data
    """

    def __init__(self, 
                 report_data_df: pd.DataFrame, 
                 data_type: str ='outbound') -> None:
        """
        Initialize SKU Mapper with report data and memory management
        
        Args:
            report_data_df (pd.DataFrame): Raw sales/return data from marketplace
            data_type (str): 'outbound' or 'return' to specify data type
        """
        self.report_data_df = report_data_df.copy()
        self.data_type = data_type

        # 2. Implement a Master Mapping Loader: Load and manage mapping data (PART 1)
        self.mapping_df = None
        self.inventory_df = None
        self.processed_df = None
        self.unmapped_skus = []

        # Set up Memory
        # Cache
        self.memory_combos_path = Path('memory/combo_sku_memory.csv')
        self.memory_inventory_path = Path('memory/inventory_memory.csv')
        self.memory_mapping_path = Path('clean_data/sku_mappings_final_clean.csv')

        # Master paths: Intial data
        self.master_combos_path = Path('clean_data/combo_sku_clean.csv')
        self.master_inventory_path = Path('clean_data/cleaned_inventory.csv')
        self.master_mapping_path = Path('clean_data/sku_mappings_final_clean.csv')
        

        # Create memory directory if it doesn't exist
        Path('memory').mkdir(exist_ok=True)

        # Setup logging FIRST (before any log calls)
        self._setup_logging()

        # Initialize mapping and inventory data
        self._initialize_memory_system()

       

    def _initialize_memory_system(self) -> None:
        """Initialize mapping and inventory data from memory or master files"""
        try:
            # Load mapping data
            if self._is_valid_csv(self.memory_mapping_path):
                self.mapping_df = pd.read_csv(self.memory_mapping_path)
                self.log_mapping_process("SYSTEM", "LOADED", f"Mapping data loaded from memory: {self.memory_mapping_path}")
            else:
                self.mapping_df = pd.read_csv(self.master_mapping_path)
                self.log_mapping_process("SYSTEM", "LOADED", f"Mapping data loaded from master file: {self.master_mapping_path}")

            # Load combo SKU data
            if self._is_valid_csv(self.memory_combos_path):
                self.combo_sku_df = pd.read_csv(self.memory_combos_path)
                self.log_mapping_process("SYSTEM", "LOADED", f"Combo SKU data loaded from memory: {self.memory_combos_path}")
            else:
                self.combo_sku_df = pd.read_csv(self.master_combos_path)
                self.log_mapping_process("SYSTEM", "LOADED", f"Combo SKU data loaded from master file: {self.master_combos_path}")
                
            # Load inventory data  
            if self._is_valid_csv(self.memory_inventory_path):
                self.inventory_df = pd.read_csv(self.memory_inventory_path)
                self.log_mapping_process("SYSTEM", "LOADED", f"Inventory data loaded from memory: {self.memory_inventory_path}")
            else:
                self.inventory_df = pd.read_csv(self.master_inventory_path)
                self.log_mapping_process("SYSTEM", "LOADED", f"Inventory data loaded from master file: {self.master_inventory_path}")
                
        except Exception as e:
            self.log_mapping_process("SYSTEM", "ERROR", f"Failed to initialize memory system: {str(e)}")
            raise SystemError(f"Memory Initialization failed: {str(e)}")

    def _is_valid_csv(self, file_path):
        """Check if CSV file exists and has valid data"""
        try:
            if not file_path.exists():
                return False
            
            # Try to read the file and check if it has data
            df = pd.read_csv(file_path)
            return not df.empty and len(df.columns) > 0
            
        except (pd.errors.EmptyDataError, pd.errors.ParserError, FileNotFoundError):
            return False
        except Exception:
            return False

    def log_mapping_process(self, sku, msku, status):
        """Log mapping process for audit trail"""
        log_message = f"SKU: {sku} | MSKU: {msku} | Status: {status}"
        logging.info(log_message)
        print(log_message)  # Also print to console for debugging


    
    def _setup_logging(self) -> None:
        """Setup logging for mapping process"""
        # Create logs directory FIRST
        Path('logs').mkdir(exist_ok=True)
        
        # THEN setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/sku_mapping.log'),
                logging.StreamHandler()
            ]
        )

    def _normalize_column_names(self, df):
        """
        Normalize column names to standard format
        Args:
            df (pd.DataFrame): DataFrame with potentially non-standard column names
        Returns:
            pd.DataFrame: DataFrame with normalized column names
        """
        # Create a mapping of various column name formats to standard names
        column_mapping = {
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
        
        # Apply column mapping
        df_normalized = df.rename(columns=column_mapping)
        
        # Also convert all column names to lowercase as fallback
        df_normalized.columns = df_normalized.columns.str.lower().str.strip()
        
        return df_normalized

    def _validate_required_columns(self, df, required_columns=['sku', 'msku', 'panels']):
        """
        Validate that required columns exist in the dataframe
        Args:
            df (pd.DataFrame): DataFrame to validate
            required_columns (list): List of required column names (default: composite key columns)
        Returns:
            bool: True if all required columns exist, False otherwise
            str: Error message if validation fails
        """
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            available_columns = list(df.columns)
            error_msg = f"Missing required columns: {missing_columns}. Available columns: {available_columns}"
            return False, error_msg
        
        return True, "All required columns present"

    # 2. Implement a Master Mapping Loader: Load and manage mapping data (PART 2)
    def load_mapping_data(self, mapping_file_path=None, delete_existing=False):
        """
        Load additional mapping data from a file if delete_existing is False
        or reset mapping data if delete_existing is True
        Args:
            mapping_file_path (str): Path to the mapping file to load
            delete_existing (bool): Whether to delete existing mapping data
        """
        try:
            if delete_existing:
                if mapping_file_path and self._is_valid_csv(mapping_file_path):
                    # Load and normalize the new mapping data
                    new_mapping_df = pd.read_csv(mapping_file_path)
                    new_mapping_df = self._normalize_column_names(new_mapping_df)
                    
                    # Validate required columns (sku, msku, panels)
                    is_valid, error_msg = self._validate_required_columns(new_mapping_df, ['sku', 'msku', 'panels'])
                    if not is_valid:
                        self.log_mapping_process("LOAD", "ERROR", f"Column validation failed: {error_msg}")
                        return
                    
                    # Clean and set as new mapping data using composite key (sku + panels)
                    self.mapping_df = new_mapping_df.drop_duplicates(['sku', 'panels']).dropna(subset=['sku', 'msku', 'panels'])
                    self.save_mapping_to_memory()
                    self.log_mapping_process("LOAD", "RESET", f"Existing mapping data reset to {mapping_file_path}")
                    
            else:
                if mapping_file_path and self._is_valid_csv(mapping_file_path):
                    # Load and normalize additional mapping data
                    additional_mapping = pd.read_csv(mapping_file_path)
                    additional_mapping = self._normalize_column_names(additional_mapping)
                    
                    # Validate required columns (sku, msku, panels)
                    is_valid, error_msg = self._validate_required_columns(additional_mapping, ['sku', 'msku', 'panels'])
                    if not is_valid:
                        self.log_mapping_process("LOAD", "ERROR", f"Column validation failed: {error_msg}")
                        return
                    
                    # Clean and merge with existing data using composite key (sku + panels)
                    additional_mapping = additional_mapping.drop_duplicates(['sku', 'panels']).dropna(subset=['sku', 'msku', 'panels'])
                    self.mapping_df = pd.concat([self.mapping_df, additional_mapping]).drop_duplicates(['sku', 'panels'])
                    self.save_mapping_to_memory()
                    self.log_mapping_process("LOAD", "SUCCESS", f"Additional mapping data loaded from {mapping_file_path}")
                    
        except Exception as e:
            self.log_mapping_process("LOAD", "ERROR", f"Failed to load mapping data: {str(e)}")

    def save_mapping_to_memory(self):
        """Save current mapping data to memory with normalization"""
        try:
            if self.mapping_df is not None:
                # Normalize before saving
                normalized_df = self._normalize_column_names(self.mapping_df)
                normalized_df.to_csv(self.memory_mapping_path, index=False)
                self.log_mapping_process("SAVE", "SUCCESS", f"Mapping data saved to memory: {self.memory_mapping_path}")
        except Exception as e:
            self.log_mapping_process("SAVE", "ERROR", f"Failed to save mapping data: {str(e)}")

    # 3. Develop SKU Identification/Mapping Function
    def handle_sku_mappings(self):
        """Process entire dataframe and map all SKUs"""
        try:
            # Normalize column names
            self.report_data_df = self._normalize_column_names(self.report_data_df)
            
            # Check if msku column doesn't exist or has null values
            if 'msku' not in self.report_data_df.columns or self.report_data_df['msku'].isnull().all():
                # Validate required columns
                is_valid, error_msg = self._validate_required_columns(self.report_data_df, ['sku'])
                if not is_valid:
                    self.log_mapping_process("PROCESS", "ERROR", f"Column validation failed: {error_msg}")
                    return
                
                # Check if sku is a combo sku
                
                # Map SKUs to MSKUs
                self.report_data_df['msku'] = self.report_data_df['sku'].apply(self.map_sku)
            
            # Identify unmapped SKUs
            self.unmapped_skus = self.report_data_df[self.report_data_df['msku'].isnull()]['sku'].unique().tolist()
            
            # Log unmapped SKUs
            if self.unmapped_skus:
                self.log_mapping_process("PROCESS", "UNMAPPED", f"Unmapped SKUs found: {self.unmapped_skus}")
            
            # Save processed data
            self.processed_df = self.report_data_df.dropna(subset=['msku'])
            self.log_mapping_process("PROCESS", "SUCCESS", "SKU mapping completed successfully")
            
        except Exception as e:
            self.log_mapping_process("PROCESS", "ERROR", f"Failed to process SKU mappings: {str(e)}")

    def map_sku(self, sku):
        """Map individual SKU to MSKU using hashtable"""
        try:
            # Create hashtable if not exists
            if not hasattr(self, '_sku_hashtable'):
                self._sku_hashtable = dict(zip(self.mapping_df['sku'], self.mapping_df['msku']))
            
            result = self._sku_hashtable.get(sku)
            return result if result is not None else None
        except:
            return None
    
    # 4. Add Combo Product Handling: Support products that may have multiple SKUs
    def process_combo_sku(self, combo_sku):
        pass

    def is_combo_sku(self, sku):
        """Check if SKU is a combo SKU"""
        try:
            # Create combo hashtable if not exists
            if not hasattr(self, '_combo_sku_hashtable'):
                self._combo_sku_hashtable = {}
                
                # Get all combo SKUs from the "Combo" column
                combo_skus = self.combo_sku_df['Combo'].dropna()  # Remove NA values
                combo_skus = combo_skus[combo_skus != 'NA']  # Remove 'NA' strings
                
                # Set all combo SKUs to True in hashtable
                for combo_sku in combo_skus:
                    self._combo_sku_hashtable[combo_sku] = True
            
            return self._combo_sku_hashtable.get(sku, False)
        except:
            return False


    def handle_multiple_skus(self, sku_list):
        # just a loop with map_sku
        pass

    # Enhanced Features
    def validate_sku_format(self, sku):
        pass
    
    def handle_missing_mappings(self, unmapped_skus):
        pass


# 5. Build a Flexible Input Processor: Allow 
# various input formats for sales data 
# i.e daily reports data
report_data = pd.read_csv('daily_reports/cste_amazon/cste_amazon.csv')
sk_mapper = SKU_Mapper(report_data)
