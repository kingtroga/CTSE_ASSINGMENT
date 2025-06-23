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
