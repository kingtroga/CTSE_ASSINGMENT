"""
Core FlexibleInputProcessor class.
Main orchestrator for processing various file formats into pandas DataFrames.
"""

import pandas as pd
from pathlib import Path
import logging
from typing import Union, Dict, Any, Optional

from .dependencies import DependencyManager
from .readers import FileReaders
from .utils import clean_dataframe, get_file_info


class FlexibleInputProcessor:
    """
    A flexible input processor that can handle various file formats
    supported by pandas and convert them to DataFrames.
    
    Supports: CSV, Excel, JSON, Parquet, TSV, Pickle, HDF5, Feather, ORC, SAS, SPSS, Stata
    Auto-installs missing dependencies and enforces sheet specification for multi-sheet Excel files.
    """
    
    def __init__(self, encoding: str = 'utf-8', verbose: bool = True, auto_install: bool = True):
        """
        Initialize the FlexibleInputProcessor.
        
        Args:
            encoding (str): Default encoding for text files
            verbose (bool): Whether to print processing information
            auto_install (bool): Whether to automatically install missing dependencies
        """
        self.encoding = encoding
        self.verbose = verbose
        self.auto_install = auto_install
        self.logger = self._setup_logger()
        
        # Initialize components
        self.dependency_manager = DependencyManager(auto_install, self.logger)
        self.file_readers = FileReaders(self.dependency_manager, encoding, self.logger)
        
        # Mapping of file extensions to reader methods
        self.readers = {
            '.csv': self.file_readers.read_csv,
            '.tsv': self.file_readers.read_tsv,
            '.txt': self.file_readers.read_csv,  # Assume CSV-like format
            '.xlsx': self.file_readers.read_excel,
            '.xls': self.file_readers.read_excel,
            '.json': self.file_readers.read_json,
            '.parquet': self.file_readers.read_parquet,
            '.pkl': self.file_readers.read_pickle,
            '.pickle': self.file_readers.read_pickle,
            '.h5': self.file_readers.read_hdf,
            '.hdf5': self.file_readers.read_hdf,
            '.feather': self.file_readers.read_feather,
            '.orc': self.file_readers.read_orc,
            '.sas7bdat': self.file_readers.read_sas,
            '.sav': self.file_readers.read_spss,
            '.dta': self.file_readers.read_stata,
        }
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger for the processor."""
        logger = logging.getLogger('FlexibleInputProcessor')
        if not logger.handlers:
            # Create logs directory if it doesn't exist
            LOGS_DIR = Path('logs')
            LOGS_DIR.mkdir(exist_ok=True)
            
            # File handler for saving logs
            file_handler = logging.FileHandler(LOGS_DIR / 'flexible_input_processor.log')
            # Console handler for terminal output
            console_handler = logging.StreamHandler()
            
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            logger.setLevel(logging.INFO if self.verbose else logging.WARNING)
        return logger
    
    def process_file(self, 
                    file_path: Union[str, Path], 
                    sheet_name: Optional[Union[str, int]] = None,
                    **kwargs) -> pd.DataFrame:
        """
        Process a file and return a pandas DataFrame.
        
        Args:
            file_path (Union[str, Path]): Path to the input file
            sheet_name (Optional[Union[str, int]]): Sheet name for Excel files
            **kwargs: Additional arguments to pass to pandas read functions
            
        Returns:
            pd.DataFrame: Processed DataFrame
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is not supported
            Exception: For other processing errors
        """
        file_path = Path(file_path)
        
        # Check if file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get file extension
        extension = file_path.suffix.lower()
        
        if extension not in self.readers:
            raise ValueError(f"Unsupported file format: {extension}")
        
        self.logger.info(f"Processing file: {file_path}")
        self.logger.info(f"Detected format: {extension}")
        
        try:
            # Call appropriate reader function
            if extension in ['.xlsx', '.xls']:
                df = self.readers[extension](file_path, sheet_name=sheet_name, **kwargs)
            else:
                df = self.readers[extension](file_path, **kwargs)
            
            self.logger.info(f"Successfully loaded data: {df.shape[0]} rows, {df.shape[1]} columns")
            
            # Clean the DataFrame
            df = clean_dataframe(df, self.logger)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {str(e)}")
            raise
    
    def get_file_info(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Get information about the file without fully loading it.
        
        Args:
            file_path (Union[str, Path]): Path to the file
            
        Returns:
            Dict[str, Any]: File information
        """
        return get_file_info(file_path, self.file_readers)
    
    def list_excel_sheets(self, file_path: Union[str, Path]) -> list:
        """
        List all sheet names in an Excel file.
        
        Args:
            file_path (Union[str, Path]): Path to Excel file
            
        Returns:
            list: List of sheet names
        """
        return self.file_readers.list_excel_sheets(file_path)
    
    def batch_process(self, 
                     file_paths: list, 
                     combine: bool = False,
                     **kwargs) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """
        Process multiple files at once.
        
        Args:
            file_paths (list): List of file paths
            combine (bool): Whether to combine all DataFrames into one
            **kwargs: Additional arguments for processing
            
        Returns:
            Union[pd.DataFrame, Dict[str, pd.DataFrame]]: 
                Single DataFrame if combine=True, dict of DataFrames otherwise
        """
        results = {}
        
        for file_path in file_paths:
            try:
                df = self.process_file(file_path, **kwargs)
                results[str(file_path)] = df
            except Exception as e:
                self.logger.error(f"Failed to process {file_path}: {str(e)}")
                continue
        
        if combine and results:
            self.logger.info(f"Combining {len(results)} DataFrames")
            combined_df = pd.concat(results.values(), ignore_index=True)
            return combined_df
        
        return results
    
    def get_supported_formats(self) -> Dict[str, bool]:
        """
        Get a dictionary of supported file formats and their availability.
        
        Returns:
            Dict[str, bool]: Dictionary mapping format to availability
        """
        return self.dependency_manager.get_available_formats()
    
    def install_all_dependencies(self) -> Dict[str, bool]:
        """
        Install all optional dependencies for maximum format support.
        
        Returns:
            Dict[str, bool]: Installation results for each package
        """
        return self.dependency_manager.install_all_optional_dependencies()