if __name__ == "__main__":
    from sku_mapper.core.mapper import SKUMapper
    from flexible_input_processor import FlexibleInputProcessor
    from flexible_input_processor.utils import format_file_size
    from pathlib import Path
    
    # Create processor instance
    processor = FlexibleInputProcessor(verbose=True, auto_install=True)
    
    # Hard-coded file paths from the directory structure
    file_paths = [
        'raw_daily_reports/cste_amazon/cste_amazon.csv',
        'raw_daily_reports/cste_fk/cste_fk.csv', 
        'raw_daily_reports/cste_meesho/cste_meesho.csv',
        'raw_daily_reports/gl_fk/gl_fk.csv',
        'raw_daily_reports/rudrav_meesho/rudrav_meesho.csv'
        # Skipping 'other' folder as it's empty
    ]
    
    # Create output directory
    output_dir = Path('test_output_data')
    output_dir.mkdir(exist_ok=True)
    
    for file_path in file_paths:
        print(f"\n{'='*50}")
        print(f"Processing: {file_path}")
        print('='*50)
        
        try:
            # Process file using FlexibleInputProcessor
            report_data = processor.process_file(file_path)
            info = processor.get_file_info(file_path)
            
            print(f"File: {file_path}")
            print(f"Size: {format_file_size(info['file_size'])}")
            print(f"Supported: {info['supported']}")
            
            if report_data is None:
                print(f"❌ Failed to load: {file_path}")
                continue
                
            # Initialize SKU Mapper
            mapper = SKUMapper(report_data)
            
            # Process SKU mappings
            mapper.process_sku_mappings()
            
            # Update inventory
            mapper.update_inventory()
            
            # Get outbound data
            outbound_data = mapper.get_outbound_data()
            
            # Save results
            if outbound_data is not None:
                # Extract panel name for output filename
                panel_name = Path(file_path).parent.name
                output_file = output_dir / f'{panel_name}_outbound.csv'
                outbound_data.to_csv(output_file, index=False)
                print(f"✅ Saved outbound data: {output_file}")
                print(f"   Records processed: {len(outbound_data)}")
            else:
                print(f"❌ No outbound data generated for {file_path}")
            
            # Print unmapped SKUs
            if mapper.unmapped_skus:
                print(f"⚠️  Unmapped SKUs ({len(mapper.unmapped_skus)}):")
                for sku in mapper.unmapped_skus[:5]:  # Show first 5
                    print(f"  - {sku}")
                if len(mapper.unmapped_skus) > 5:
                    print(f"  ... and {len(mapper.unmapped_skus) - 5} more")
            else:
                print("✅ All SKUs mapped successfully")
                
        except Exception as e:
            print(f"❌ Error processing {file_path}: {str(e)}")
            continue
    
    print(f"\n{'='*50}")
    print("🎉 Batch processing completed!")
    print(f"Check output files in: {output_dir}")
    print('='*50)