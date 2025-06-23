"""
Example usage of the FlexibleInputProcessor package.
Demonstrates different ways to use the modularized file processor.
"""

# Import the main processor
from flexible_input_processor import FlexibleInputProcessor, create_processor
from flexible_input_processor import demo_usage, format_file_size

# You can also import individual components if needed
from flexible_input_processor import DependencyManager, FileReaders


def basic_usage_example():
    """Basic usage example."""
    print("=== Basic Usage Example ===")
    
    # Create processor instance
    processor = FlexibleInputProcessor(verbose=True, auto_install=True)
    
    # Example files (replace with your actual files)
    files_to_process = [
        'sales_data.csv',
        'financial_report.xlsx',
        'user_data.json'
    ]
    
    for file_path in files_to_process:
        try:
            # Get file information first
            info = processor.get_file_info(file_path)
            print(f"\nFile: {file_path}")
            print(f"Size: {format_file_size(info['file_size'])}")
            print(f"Supported: {info['supported']}")
            
            # For Excel files, check sheets
            if file_path.endswith(('.xlsx', '.xls')):
                sheets = processor.list_excel_sheets(file_path)
                print(f"Sheets: {sheets}")
                
                # Process specific sheet if multiple sheets exist
                if len(sheets) > 1:
                    df = processor.process_file(file_path, sheet_name=sheets[0])
                else:
                    df = processor.process_file(file_path)
            else:
                # Process non-Excel files
                df = processor.process_file(file_path)
            
            print(f"Shape: {df.shape}")
            print(f"Columns: {list(df.columns)[:5]}...")  # Show first 5 columns
            
        except FileNotFoundError:
            print(f"File not found: {file_path}")
        except Exception as e:
            print(f"Error: {e}")


def advanced_usage_example():
    """Advanced usage with custom settings."""
    print("\n=== Advanced Usage Example ===")
    
    # Create processor with custom settings
    processor = create_processor(
        encoding='latin-1',
        verbose=False,
        auto_install=True
    )
    
    # Check available formats
    formats = processor.get_supported_formats()
    print("Available formats:")
    for fmt, available in formats.items():
        status = "✓" if available else "✗"
        print(f"  {fmt}: {status}")
    
    # Batch processing example
    file_list = ['file1.csv', 'file2.xlsx', 'file3.json']
    
    try:
        # Process all files and combine into single DataFrame
        combined_df = processor.batch_process(file_list, combine=True)
        print(f"\nCombined data shape: {combined_df.shape}")
        
        # Or process separately
        separate_results = processor.batch_process(file_list, combine=False)
        print(f"Processed {len(separate_results)} files separately")
        
    except Exception as e:
        print(f"Batch processing error: {e}")


def dependency_management_example():
    """Example of working with dependencies."""
    print("\n=== Dependency Management Example ===")
    
    # Create dependency manager directly
    deps = DependencyManager(auto_install=True)
    
    # Check specific dependencies
    critical_packages = ['openpyxl', 'pyarrow', 'xlrd']
    
    for package in critical_packages:
        available = deps.ensure_dependency(package)
        print(f"{package}: {'Available' if available else 'Not available'}")
    
    # Install all optional dependencies at once
    print("\nInstalling all optional dependencies...")
    results = deps.install_all_optional_dependencies()
    
    for package, success in results.items():
        status = "✓ Installed" if success else "✗ Failed"
        print(f"  {package}: {status}")


def excel_specific_example():
    """Examples specific to Excel file handling."""
    print("\n=== Excel-Specific Examples ===")
    
    processor = FlexibleInputProcessor()
    
    excel_files = [
        ('single_sheet.xlsx', None),      # Auto-detect single sheet
        ('multi_sheet.xlsx', 'Summary'),  # Specific sheet by name
        ('multi_sheet.xlsx', 0),          # First sheet by index
        ('multi_sheet.xlsx', None),       # Will raise error for multi-sheet
    ]
    
    for file_path, sheet_name in excel_files:
        try:
            print(f"\nProcessing: {file_path} (sheet: {sheet_name})")
            
            # List available sheets first
            sheets = processor.list_excel_sheets(file_path)
            print(f"Available sheets: {sheets}")
            
            # Process the file
            if sheet_name is not None or len(sheets) == 1:
                df = processor.process_file(file_path, sheet_name=sheet_name)
                print(f"Success: {df.shape}")
            else:
                # This will raise an error for multi-sheet files
                df = processor.process_file(file_path)
                
        except ValueError as e:
            print(f"Error: {e}")
        except FileNotFoundError:
            print(f"File not found: {file_path}")


def custom_file_reader_example():
    """Example of using file readers directly."""
    print("\n=== Custom File Reader Example ===")
    
    # Create components separately for fine control
    deps = DependencyManager(auto_install=True)
    readers = FileReaders(deps, encoding='utf-8')
    
    # Use specific readers directly
    try:
        # Read CSV with custom parameters
        df_csv = readers.read_csv('data.csv', sep=';', decimal=',')
        print(f"CSV data: {df_csv.shape}")
        
        # Read Excel with specific parameters
        df_excel = readers.read_excel('report.xlsx', sheet_name='Data', skiprows=2)
        print(f"Excel data: {df_excel.shape}")
        
        # Read JSON with custom orientation
        df_json = readers.read_json('data.json', orient='records')
        print(f"JSON data: {df_json.shape}")
        
    except Exception as e:
        print(f"Direct reader error: {e}")


if __name__ == "__main__":
    # Run all examples
    basic_usage_example()
    advanced_usage_example()
    dependency_management_example()
    excel_specific_example()
    custom_file_reader_example()
    
    # Run the demo function
    print("\n" + "="*50)
    print("Running comprehensive demo...")
    demo_usage()