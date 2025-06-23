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
