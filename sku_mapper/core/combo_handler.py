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