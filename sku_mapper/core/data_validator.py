
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