"""
File readers module for FlexibleInputProcessor.
Contains specialized reading methods for different file formats.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Union, Optional
import logging


class FileReaders:
    """Collection of file reading methods for different formats."""
    
    def __init__(self, dependency_manager, encoding: str = 'utf-8', logger: logging.Logger = None):
        """
        Initialize file readers.
        
        Args:
            dependency_manager: DependencyManager instance
            encoding (str): Default encoding for text files
            logger (logging.Logger): Logger instance
        """
        self.deps = dependency_manager
        self.encoding = encoding
        self.logger = logger or logging.getLogger(__name__)
    
    def read_csv(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """Read CSV files with automatic delimiter detection."""
        default_kwargs = {
            'encoding': self.encoding,
            'sep': None,  # Auto-detect separator
            'engine': 'python',
            'on_bad_lines': 'skip'
        }
        default_kwargs.update(kwargs)
        
        try:
            return pd.read_csv(file_path, **default_kwargs)
        except UnicodeDecodeError:
            # Try different encodings
            for enc in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    default_kwargs['encoding'] = enc
                    self.logger.warning(f"Retrying with encoding: {enc}")
                    return pd.read_csv(file_path, **default_kwargs)
                except UnicodeDecodeError:
                    continue
            raise
    
    def read_tsv(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """Read TSV files."""
        default_kwargs = {
            'sep': '\t',
            'encoding': self.encoding,
            'on_bad_lines': 'skip'
        }
        default_kwargs.update(kwargs)
        return pd.read_csv(file_path, **default_kwargs)
    
    def read_excel(self, file_path: Path, sheet_name=None, **kwargs) -> pd.DataFrame:
        """
        Read Excel files with mandatory sheet specification for multi-sheet files.
        
        Args:
            file_path (Path): Path to Excel file
            sheet_name: Sheet name or index to read
            **kwargs: Additional arguments
            
        Returns:
            pd.DataFrame: Loaded DataFrame
            
        Raises:
            ValueError: If multiple sheets exist and no sheet is specified
            ImportError: If required Excel dependencies are missing
        """
        # Ensure required dependencies
        if file_path.suffix.lower() == '.xlsx':
            if not self.deps.ensure_dependency('openpyxl'):
                raise ImportError("openpyxl is required for .xlsx files")
            engine = 'openpyxl'
        else:  # .xls
            if not self.deps.ensure_dependency('xlrd'):
                raise ImportError("xlrd is required for .xls files")
            engine = 'xlrd'
        
        # First, check the number of sheets
        try:
            xl_file = pd.ExcelFile(file_path, engine=engine)
            sheet_names = xl_file.sheet_names
            num_sheets = len(sheet_names)
            
            self.logger.info(f"Excel file contains {num_sheets} sheet(s): {sheet_names}")
            
            # If multiple sheets and no sheet specified, raise error
            if num_sheets > 1 and sheet_name is None:
                raise ValueError(
                    f"Excel file contains {num_sheets} sheets: {sheet_names}. "
                    f"You must specify which sheet to read using the 'sheet_name' parameter. "
                    f"Examples: sheet_name='{sheet_names[0]}' or sheet_name=0"
                )
            
            # Use first sheet if only one sheet and no sheet specified
            if num_sheets == 1 and sheet_name is None:
                sheet_name = sheet_names[0]
                self.logger.info(f"Using only available sheet: {sheet_name}")
            
        except Exception as e:
            self.logger.error(f"Error reading Excel file structure: {e}")
            raise
        
        # Read the specified sheet
        default_kwargs = {
            'sheet_name': sheet_name,
            'engine': engine
        }
        default_kwargs.update(kwargs)
        
        try:
            return pd.read_excel(file_path, **default_kwargs)
        except Exception as e:
            # Provide helpful error message if sheet doesn't exist
            if "Worksheet named" in str(e) or "sheet" in str(e).lower():
                raise ValueError(
                    f"Sheet '{sheet_name}' not found. Available sheets: {sheet_names}"
                )
            raise
    
    def read_json(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """Read JSON files with fallback to JSON Lines format."""
        default_kwargs = {
            'encoding': self.encoding,
            'lines': False  # Try normal JSON first
        }
        default_kwargs.update(kwargs)
        
        try:
            return pd.read_json(file_path, **default_kwargs)
        except ValueError:
            # Try JSON Lines format
            default_kwargs['lines'] = True
            self.logger.warning("Retrying as JSON Lines format")
            return pd.read_json(file_path, **default_kwargs)
    
    def read_parquet(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """Read Parquet files with auto-dependency installation."""
        # Try pyarrow first, then fastparquet
        if not self.deps.ensure_dependency('pyarrow'):
            if not self.deps.ensure_dependency('fastparquet'):
                raise ImportError("Either pyarrow or fastparquet is required for parquet files")
            else:
                kwargs['engine'] = 'fastparquet'
        
        return pd.read_parquet(file_path, **kwargs)
    
    def read_pickle(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """Read Pickle files."""
        return pd.read_pickle(file_path, **kwargs)
    
    def read_hdf(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """Read HDF5 files with auto-dependency installation."""
        if not self.deps.ensure_dependency('tables'):
            raise ImportError("tables (PyTables) is required for HDF5 files")
        
        if 'key' not in kwargs:
            # Try to find the first available key
            with pd.HDFStore(file_path, 'r') as store:
                keys = store.keys()
                if keys:
                    kwargs['key'] = keys[0]
                    self.logger.info(f"Using HDF5 key: {keys[0]}")
                else:
                    raise ValueError("No keys found in HDF5 file")
        return pd.read_hdf(file_path, **kwargs)
    
    def read_feather(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """Read Feather files with auto-dependency installation."""
        if not self.deps.ensure_dependency('pyarrow'):
            raise ImportError("pyarrow is required for feather files")
        return pd.read_feather(file_path, **kwargs)
    
    def read_orc(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """Read ORC files with auto-dependency installation."""
        if not self.deps.ensure_dependency('pyarrow'):
            raise ImportError("pyarrow is required for ORC files")
        return pd.read_orc(file_path, **kwargs)
    
    def read_sas(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """Read SAS files with auto-dependency installation."""
        if not self.deps.ensure_dependency('pyreadstat'):
            self.logger.warning("pyreadstat not available, trying pandas built-in SAS reader")
        return pd.read_sas(file_path, **kwargs)
    
    def read_spss(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """Read SPSS files with auto-dependency installation."""
        if not self.deps.ensure_dependency('pyreadstat'):
            raise ImportError("pyreadstat is required for SPSS files")
        return pd.read_spss(file_path, **kwargs)
    
    def read_stata(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """Read Stata files."""
        # Stata is supported natively by pandas
        return pd.read_stata(file_path, **kwargs)
    
    def list_excel_sheets(self, file_path: Union[str, Path]) -> list:
        """
        List all sheet names in an Excel file.
        
        Args:
            file_path (Union[str, Path]): Path to Excel file
            
        Returns:
            list: List of sheet names
        """
        file_path = Path(file_path)
        
        if file_path.suffix.lower() not in ['.xlsx', '.xls']:
            raise ValueError("File is not an Excel file")
        
        # Ensure dependencies
        if file_path.suffix.lower() == '.xlsx':
            if not self.deps.ensure_dependency('openpyxl'):
                raise ImportError("openpyxl is required for .xlsx files")
            engine = 'openpyxl'
        else:
            if not self.deps.ensure_dependency('xlrd'):
                raise ImportError("xlrd is required for .xls files")
            engine = 'xlrd'
        
        try:
            xl_file = pd.ExcelFile(file_path, engine=engine)
            return xl_file.sheet_names
        except Exception as e:
            self.logger.error(f"Error reading Excel file: {e}")
            raise