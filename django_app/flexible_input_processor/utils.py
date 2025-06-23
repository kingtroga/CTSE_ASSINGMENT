"""
Utility functions for FlexibleInputProcessor.
Contains data cleaning, file info, and demo functions.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Union, Dict, Any
import logging


def clean_dataframe(df: pd.DataFrame, logger: logging.Logger = None) -> pd.DataFrame:
    """
    Clean the DataFrame by removing empty rows/columns and standardizing column names.
    
    Args:
        df (pd.DataFrame): Input DataFrame
        logger (logging.Logger): Logger instance
        
    Returns:
        pd.DataFrame: Cleaned DataFrame
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    original_shape = df.shape
    
    # Remove completely empty rows and columns
    df = df.dropna(how='all').dropna(axis=1, how='all')
    
    # Clean column names
    df.columns = df.columns.astype(str)
    df.columns = df.columns.str.strip()
    
    # Replace empty strings with NaN
    df = df.replace('', np.nan)
    
    if df.shape != original_shape:
        logger.info(f"Cleaned data: {original_shape} -> {df.shape}")
    
    return df


def get_file_info(file_path: Union[str, Path], file_readers=None) -> Dict[str, Any]:
    """
    Get information about the file without fully loading it.
    
    Args:
        file_path (Union[str, Path]): Path to the file
        file_readers: FileReaders instance for Excel sheet listing
        
    Returns:
        Dict[str, Any]: File information
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Supported extensions
    supported_extensions = {
        '.csv', '.tsv', '.txt', '.xlsx', '.xls', '.json', '.parquet',
        '.pkl', '.pickle', '.h5', '.hdf5', '.feather', '.orc',
        '.sas7bdat', '.sav', '.dta'
    }
    
    info = {
        'file_path': str(file_path),
        'file_size': file_path.stat().st_size,
        'file_extension': file_path.suffix.lower(),
        'supported': file_path.suffix.lower() in supported_extensions
    }
    
    # Try to get additional info for Excel files
    if file_path.suffix.lower() in ['.xlsx', '.xls'] and file_readers:
        try:
            sheets = file_readers.list_excel_sheets(file_path)
            info['sheet_names'] = sheets
            info['num_sheets'] = len(sheets)
        except Exception as e:
            info['excel_error'] = str(e)
    
    return info


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes (int): Size in bytes
        
    Returns:
        str: Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def demo_usage():
    """Demonstrate usage of the FlexibleInputProcessor."""
    # Import here to avoid circular imports
    from .core import FlexibleInputProcessor
    
    # Initialize processor with auto-install enabled
    processor = FlexibleInputProcessor(verbose=True, auto_install=True)
    
    # Example file paths (you would replace these with actual file paths)
    example_files = [
        'sales_data.csv',
        'monthly_report.xlsx',
        'data_export.json',
        'analytics.parquet'
    ]
    
    print("=== FlexibleInputProcessor Demo ===\n")
    
    # Process individual files
    for file_path in example_files:
        try:
            # Get file info first
            info = processor.get_file_info(file_path)
            print(f"File Info for {file_path}:")
            print(f"  - Size: {format_file_size(info['file_size'])}")
            print(f"  - Extension: {info['file_extension']}")
            print(f"  - Supported: {info['supported']}")
            
            # Special handling for Excel files
            if file_path.endswith(('.xlsx', '.xls')):
                try:
                    sheets = processor.list_excel_sheets(file_path)
                    print(f"  - Sheets: {sheets}")
                    
                    if len(sheets) > 1:
                        print(f"  - Multi-sheet file detected. You must specify sheet_name!")
                        print(f"  - Example: processor.process_file('{file_path}', sheet_name='{sheets[0]}')")
                        # Process with first sheet as example
                        df = processor.process_file(file_path, sheet_name=sheets[0])
                    else:
                        # Single sheet - can process without specifying
                        df = processor.process_file(file_path)
                        
                except FileNotFoundError:
                    print(f"  - File not found for sheet listing")
                    continue
            else:
                # Process non-Excel files normally
                df = processor.process_file(file_path)
            
            print(f"  - Shape: {df.shape}")
            print(f"  - Columns: {list(df.columns)}")
            print()
            
        except FileNotFoundError:
            print(f"File not found: {file_path}")
        except ValueError as e:
            if "sheets" in str(e):
                print(f"Excel sheet error: {e}")
            else:
                print(f"Value error: {e}")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Excel-specific examples
    print("\n=== Excel File Examples ===")
    excel_examples = [
        ("single_sheet.xlsx", None),  # Will work automatically
        ("multi_sheet.xlsx", None),   # Will raise error
        ("multi_sheet.xlsx", "Sales"), # Will work
        ("multi_sheet.xlsx", 0),      # Will work (first sheet)
    ]
    
    for file_path, sheet_name in excel_examples:
        try:
            if sheet_name is None:
                print(f"\nTrying: processor.process_file('{file_path}')")
                df = processor.process_file(file_path)
            else:
                print(f"\nTrying: processor.process_file('{file_path}', sheet_name='{sheet_name}')")
                df = processor.process_file(file_path, sheet_name=sheet_name)
            
            print(f"  ✓ Success: {df.shape}")
            
        except ValueError as e:
            print(f"  ✗ Error: {e}")
        except FileNotFoundError:
            print(f"  ✗ File not found: {file_path}")
        except Exception as e:
            print(f"  ✗ Other error: {e}")
    
    # Batch processing example
    try:
        print(f"\n=== Batch Processing ===")
        results = processor.batch_process(example_files, combine=False)
        print(f"Batch processed {len(results)} files successfully")
    except Exception as e:
        print(f"Batch processing error: {e}")
    
    # Dependency installation example
    print(f"\n=== Dependency Management ===")
    dependencies_to_test = ['openpyxl', 'pyarrow', 'xlrd']
    for dep in dependencies_to_test:
        available = processor.dependency_manager.ensure_dependency(dep)
        print(f"  - {dep}: {'✓ Available' if available else '✗ Not available'}")
    
    # Show available formats
    print(f"\n=== Available Formats ===")
    available_formats = processor.dependency_manager.get_available_formats()
    for fmt, available in available_formats.items():
        status = '✓' if available else '✗'
        print(f"  - {fmt}: {status}")


if __name__ == "__main__":
    demo_usage()