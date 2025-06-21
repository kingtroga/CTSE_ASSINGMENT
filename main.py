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

    # Updated handle_sku_mappings with better error handling
    def handle_sku_mappings(self):
        """Process entire dataframe and map all SKUs"""
        try:
            print("=== Starting SKU Mapping Process ===")
            
            # Debug: Check original columns
            print(f"Original columns: {list(self.report_data_df.columns)}")
            
            # Normalize column names
            self.report_data_df = self._normalize_column_names(self.report_data_df)
            print(f"Normalized columns: {list(self.report_data_df.columns)}")
            
            # Check if msku column doesn't exist or has null values
            if 'msku' not in self.report_data_df.columns or self.report_data_df['msku'].isnull().all():
                print("MSKU column missing or empty, proceeding with SKU mapping...")
                
                # Validate required columns
                is_valid, error_msg = self._validate_required_columns(self.report_data_df, ['sku'])
                if not is_valid:
                    print(f"Validation failed: {error_msg}")
                    self.log_mapping_process("PROCESS", "ERROR", f"Column validation failed: {error_msg}")
                    return
                
                print("SKU column found, proceeding with mapping...")
                # Map SKUs to MSKUs (handles both regular and combo SKUs)
                self.report_data_df['msku'] = self.report_data_df['sku'].apply(self.map_sku_with_combo_check)
            else:
                print("MSKU column already exists and has data")
            
            # Identify unmapped SKUs
            if 'sku' in self.report_data_df.columns:
                self.unmapped_skus = self.report_data_df[self.report_data_df['msku'].isnull()]['sku'].unique().tolist()
            
            # Log unmapped SKUs
            if self.unmapped_skus:
                print(f"Found {len(self.unmapped_skus)} unmapped SKUs")
                self.log_mapping_process("PROCESS", "UNMAPPED", f"Unmapped SKUs found: {self.unmapped_skus}")
            
            # Save processed data
            self.processed_df = self.report_data_df.dropna(subset=['msku'])
            print(f"Processing complete. Final DataFrame shape: {self.processed_df.shape}")
            self.log_mapping_process("PROCESS", "SUCCESS", "SKU mapping completed successfully")
            
        except Exception as e:
            print(f"Exception occurred: {str(e)}")
            print(f"Exception type: {type(e)}")
            import traceback
            traceback.print_exc()
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
        
    def map_sku_with_combo_check(self, sku):
        """Map SKU to MSKU, handling combo SKUs"""
        try:
            if self.is_combo_sku(sku):
                # Get regular SKUs from combo
                regular_skus = self.process_combo_sku(sku)
                
                if isinstance(regular_skus, list):
                    # Multiple SKUs - map each and return as list or concatenated string
                    mskus = self.handle_multiple_skus(regular_skus)
                    return mskus if len(mskus) > 1 else (mskus[0] if mskus else None)
                else:
                    # Single SKU - map it normally
                    return self.map_sku(regular_skus) if regular_skus else None
            else:
                # Regular SKU - map normally
                return self.map_sku(sku)
        except:
            return None
    
    # 4. Add Combo Product Handling: Support products that may have multiple SKUs
    def process_combo_sku(self, combo_sku):
        """Get regular SKUs associated with a combo SKU"""
        try:
            # Find the row with this combo SKU
            combo_row = self.combo_sku_df[self.combo_sku_df['Combo'] == combo_sku]
            
            if combo_row.empty:
                return []
            
            # Get all SKU columns (SKU1, SKU2, SKU3, etc.)
            sku_columns = [col for col in self.combo_sku_df.columns if col.startswith('SKU')]
            
            # Extract regular SKUs from the combo row
            regular_skus = []
            for col in sku_columns:
                sku_value = combo_row[col].iloc[0]  # Get first (and should be only) row
                if sku_value is not None and str(sku_value) != 'nan' and str(sku_value) != 'NA':
                    regular_skus.append(sku_value)
            
            return regular_skus if len(regular_skus) > 1 else (regular_skus[0] if regular_skus else None)
            
        except Exception as e:
            self.log_mapping_process("COMBO", "ERROR", f"Failed to process combo SKU {combo_sku}: {str(e)}")
            return []


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
        """Map multiple SKUs to their MSKUs"""
        try:
            return [self.map_sku(sku) for sku in sku_list if sku is not None]
        except:
            return []
        
    
    def update_inventory_memory(self):
        """
        Update inventory memory with current inventory data
        and the processed report data to get the warehouse that will fulfill the order
        and an updated inventory save that to memory/inventory_memory.csv which is just 
        a copy of clean_data/cleaned_inventory.csv and add the column last_updated
        """
        try:
            from datetime import datetime
            
            # Start with a fresh copy of the cleaned inventory
            updated_inventory = self.inventory_df.copy()
            
            # Verify we have a valid inventory DataFrame
            if updated_inventory is None or updated_inventory.empty:
                self.log_mapping_process("INVENTORY", "ERROR", "Inventory DataFrame is empty or None")
                return
                
            print(f"Starting inventory update with {len(updated_inventory)} products")
            
            # Add last_updated column
            updated_inventory['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Get warehouse columns (all columns that are warehouse codes)
            warehouse_columns = ['TLCQ', 'BLR7', 'BLR8', 'BOM5', 'BOM7', 'CCU1', 'CCX1', 
                            'DEL4', 'DEL5', 'DEX3', 'PNQ2', 'PNQ3', 'SDED', 'SDEE', 'XHJ9']
            
            # Create a copy of processed_df to avoid modifying the original
            orders_to_process = self.processed_df.copy()
            
            # Add warehouse column if it doesn't exist
            if 'warehouse' not in orders_to_process.columns:
                orders_to_process['warehouse'] = 'TLCQ'  # Default warehouse
            
            # Process each order safely
            if orders_to_process is not None and not orders_to_process.empty:
                for idx in range(len(orders_to_process)):
                    try:
                        msku = orders_to_process.iloc[idx]['msku']
                        quantity = orders_to_process.iloc[idx]['quantity']
                        
                        # Find matching product in inventory using explicit indexing
                        inventory_matches = updated_inventory[updated_inventory['msku'] == msku]
                        
                        if not inventory_matches.empty:
                            # Get the first matching product's index
                            product_idx = inventory_matches.index[0]
                            
                            # Find best warehouse to fulfill order (highest stock > 0)
                            warehouse_stocks = {}
                            for wh in warehouse_columns:
                                if wh in updated_inventory.columns:
                                    stock = updated_inventory.at[product_idx, wh]
                                    if pd.notna(stock) and stock > 0:
                                        warehouse_stocks[wh] = stock
                            
                            if warehouse_stocks:
                                # Select warehouse with highest stock
                                fulfilling_warehouse = max(warehouse_stocks, key=warehouse_stocks.get)
                                
                                # Update inventory by subtracting quantity safely
                                current_stock = updated_inventory.at[product_idx, fulfilling_warehouse]
                                updated_inventory.at[product_idx, fulfilling_warehouse] = current_stock - quantity
                                updated_inventory.at[product_idx, 'last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                
                                # Update the processed_df with warehouse info
                                original_idx = orders_to_process.index[idx]
                                self.processed_df.at[original_idx, 'warehouse'] = fulfilling_warehouse
                                
                                self.log_mapping_process("INVENTORY", "UPDATED", 
                                                    f"MSKU {msku}: -{quantity} from {fulfilling_warehouse}")
                            else:
                                # No positive stock available - use backtrack logic
                                # Find warehouse with highest stock (least negative or zero)
                                best_warehouse = None
                                best_stock = float('-inf')
                                
                                for wh in warehouse_columns:
                                    if wh in updated_inventory.columns:
                                        stock = updated_inventory.at[product_idx, wh]
                                        if pd.notna(stock) and stock > best_stock:
                                            best_stock = stock
                                            best_warehouse = wh
                                
                                # If no warehouse found, use default
                                if best_warehouse is None:
                                    best_warehouse = 'TLCQ'  # Default warehouse
                                    best_stock = 0
                                
                                # Update inventory with negative stock (backtrack)
                                updated_inventory.at[product_idx, best_warehouse] = best_stock - quantity
                                updated_inventory.at[product_idx, 'last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                
                                # Update the processed_df with warehouse info
                                original_idx = orders_to_process.index[idx]
                                self.processed_df.at[original_idx, 'warehouse'] = best_warehouse
                                
                                self.log_mapping_process("INVENTORY", "BACKTRACK", 
                                                    f"MSKU {msku}: -{quantity} from {best_warehouse} (stock went negative: {best_stock - quantity})")

                        else:
                            # MSKU not found in inventory
                            original_idx = orders_to_process.index[idx]
                            self.processed_df.at[original_idx, 'warehouse'] = 'NOT_FOUND'
                            self.log_mapping_process("INVENTORY", "NOT_FOUND", 
                                                f"MSKU {msku}: Not found in inventory")
                                                
                    except Exception as order_error:
                        self.log_mapping_process("INVENTORY", "ORDER_ERROR", 
                                            f"Failed to process order {idx}: {str(order_error)}")
                        continue
            
            # Verify DataFrame is still valid before saving
            if updated_inventory is not None and not updated_inventory.empty:
                print(f"Saving inventory with {len(updated_inventory)} products to {self.memory_inventory_path}")
                
                # Save updated inventory to memory
                updated_inventory.to_csv(self.memory_inventory_path, index=False)
                self.inventory_df = updated_inventory  # Update the class attribute
                
                self.log_mapping_process("INVENTORY", "SAVED", 
                                    f"Updated inventory saved to {self.memory_inventory_path} with {len(updated_inventory)} records")
            else:
                self.log_mapping_process("INVENTORY", "ERROR", "Updated inventory DataFrame is invalid")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.log_mapping_process("INVENTORY", "ERROR", f"Failed to update inventory: {str(e)}")

    def process_outbound_data(self):
        """
        What makes up outbound data?
        are the columns: [date, panel, sku, msku, quantity, warehouse]
        """
        try:
            if self.processed_df is None:
                self.log_mapping_process("OUTBOUND", "ERROR", "No processed data available. Run handle_sku_mappings first.")
                return None
            
            outbound_df = self.processed_df.copy()
            
            # Add missing columns with defaults
            from datetime import datetime
            
            # Add date if missing
            if 'order date' in outbound_df.columns:
                outbound_df['date'] = outbound_df['order date']
            elif 'date' not in outbound_df.columns:
                outbound_df['date'] = datetime.now().strftime('%Y-%m-%d')
            
            # Add panel if missing (use marketplace identifier)
            if 'panels' in outbound_df.columns:
                outbound_df['panel'] = outbound_df['panels']
            elif 'panel' not in outbound_df.columns:
                outbound_df['panel'] = 'unknown'  # Default panel
            
            # Ensure warehouse column exists
            if 'warehouse' not in outbound_df.columns:
                outbound_df['warehouse'] = 'TLCQ'  # Default warehouse
            
            # Replace NO_STOCK and NOT_FOUND with default warehouse
            outbound_df['warehouse'] = outbound_df['warehouse'].replace(['NO_STOCK', 'NOT_FOUND'], 'TLCQ')
            
            # Select only the required columns in the correct order
            required_columns = ['date', 'panel', 'sku', 'msku', 'quantity', 'warehouse']
            
            # Check which columns actually exist
            available_columns = []
            for col in required_columns:
                if col in outbound_df.columns:
                    available_columns.append(col)
                else:
                    self.log_mapping_process("OUTBOUND", "WARNING", f"Column '{col}' missing")
            
            # Select available columns
            outbound_df = outbound_df[available_columns]
            
            # Remove any rows with critical missing data
            critical_columns = ['sku', 'msku', 'quantity']
            available_critical = [col for col in critical_columns if col in outbound_df.columns]
            outbound_df = outbound_df.dropna(subset=available_critical)
            
            # Store as class attribute
            self.outbound_data = outbound_df
            
            self.log_mapping_process("OUTBOUND", "SUCCESS", 
                                f"Outbound data processed: {len(outbound_df)} records with columns: {list(outbound_df.columns)}")
            
            return outbound_df
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.log_mapping_process("OUTBOUND", "ERROR", f"Failed to process outbound data: {str(e)}")
            return None
    def process_inbound_data(self):
        pass
      
    # Enhanced Features
    def validate_sku_format(self, sku):
        pass
    
    def handle_missing_mappings(self, unmapped_skus):
        pass


# 5. Build a Flexible Input Processor: Allow 
# various input formats for sales data 
# i.e daily reports data
report_data = pd.read_csv('raw_daily_reports/rudrav_meesho/rudrav_meesho.csv')
sk_mapper = SKU_Mapper(report_data)
sk_mapper.handle_sku_mappings()
print(sk_mapper.processed_df.head(10))
sk_mapper.processed_df.to_csv('rudrav_meesho_processed.csv', index=False)
# After handle_sku_mappings()
sk_mapper.update_inventory_memory()  # Updates inventory with stock deductions


# Access the results
outbound_orders = sk_mapper.process_outbound_data()
outbound_orders.to_csv('outbound_orders.csv', index=False)
print("=" * 50 + "\n")

print("Unmapped SKUs:")
for sku in sk_mapper.unmapped_skus:
    print(sku)