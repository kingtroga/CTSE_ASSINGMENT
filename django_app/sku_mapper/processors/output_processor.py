import pandas as pd
from datetime import datetime
from ..utils.constants import Config
from ..core_code.logger import WMSLogger

class OutputProcessor:
    """Handles output data formatting and processing"""
    
    def __init__(self, logger: WMSLogger):
        self.logger = logger
    
    def format_outbound_data(self, processed_df: pd.DataFrame, marketplace) -> pd.DataFrame:
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
                outbound_df['panel'] = marketplace
            
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