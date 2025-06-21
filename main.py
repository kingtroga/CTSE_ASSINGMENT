if __name__ == "__main__":
    from sku_mapper.core.mapper import SKUMapper
    from flexible_input_processor import FlexibleInputProcessor
    from flexible_input_processor.utils import format_file_size

    # Create processor instance
    processor = FlexibleInputProcessor(verbose=True, auto_install=True)
    file_path = 'raw_daily_reports/rudrav_meesho/rudrav_meesho.csv'
    report_data = processor.process_file(file_path)
    info = processor.get_file_info(file_path)
    print(f"\nFile: {file_path}")
    print(f"Size: {format_file_size(info['file_size'])}")
    print(f"Supported: {info['supported']}")

    
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
        outbound_data.to_csv('outbound_orders.csv', index=False)
    
    # Print unmapped SKUs
    if mapper.unmapped_skus:
        print("Unmapped SKUs:")
        for sku in mapper.unmapped_skus:
            print(f"  - {sku}")