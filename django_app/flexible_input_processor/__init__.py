"""
FlexibleInputProcessor Package

A flexible input processor that can handle various file formats
supported by pandas and convert them to DataFrames.

Features:
- Support for CSV, Excel, JSON, Parquet, TSV, Pickle, HDF5, Feather, ORC, SAS, SPSS, Stata
- Automatic dependency installation
- Mandatory sheet specification for multi-sheet Excel files
- Robust error handling and logging
- Batch processing capabilities
"""

from .core import FlexibleInputProcessor
from .dependencies import DependencyManager
from .readers import FileReaders
from .utils import clean_dataframe, get_file_info, format_file_size, demo_usage

__version__ = "1.0.0"
__author__ = "Tari Yekorogha"
__email__ = "tariyekorogha@gmail.com"
__description__ = "Flexible file input processor for pandas DataFrames"

# Main exports
__all__ = [
    'FlexibleInputProcessor',
    'DependencyManager', 
    'FileReaders',
    'clean_dataframe',
    'get_file_info',
    'format_file_size',
    'demo_usage'
]

# Convenience function for quick access
def create_processor(encoding='utf-8', verbose=True, auto_install=True):
    """
    Create a FlexibleInputProcessor instance with common settings.
    
    Args:
        encoding (str): Default encoding for text files
        verbose (bool): Whether to print processing information
        auto_install (bool): Whether to automatically install missing dependencies
        
    Returns:
        FlexibleInputProcessor: Configured processor instance
    """
    return FlexibleInputProcessor(
        encoding=encoding, 
        verbose=verbose, 
        auto_install=auto_install
    )


# Package-level constants
SUPPORTED_FORMATS = {
    'text': ['.csv', '.tsv', '.txt'],
    'excel': ['.xlsx', '.xls'],
    'json': ['.json'],
    'binary': ['.parquet', '.pkl', '.pickle', '.h5', '.hdf5', '.feather', '.orc'],
    'statistical': ['.sas7bdat', '.sav', '.dta']
}

REQUIRED_DEPENDENCIES = {
    '.xlsx': ['openpyxl'],
    '.xls': ['xlrd'],
    '.parquet': ['pyarrow', 'fastparquet'],
    '.feather': ['pyarrow'],
    '.orc': ['pyarrow'],
    '.h5': ['tables'],
    '.hdf5': ['tables'],
    '.sav': ['pyreadstat'],
    '.sas7bdat': ['pyreadstat']
}