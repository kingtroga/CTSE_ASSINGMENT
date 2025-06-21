from pathlib import Path

class Config:
    """Configuration constants for SKU Mapper system"""
    
    # Directory paths
    MEMORY_DIR = Path('memory')
    LOGS_DIR = Path('logs') 
    CLEAN_DATA_DIR = Path('clean_data')
    RAW_REPORTS_DIR = Path('raw_daily_reports')
    
    # Memory file paths
    MEMORY_COMBOS_PATH = MEMORY_DIR / 'combo_sku_memory.csv'
    MEMORY_INVENTORY_PATH = MEMORY_DIR / 'inventory_memory.csv'
    MEMORY_MAPPING_PATH = MEMORY_DIR / 'sku_mappings_memory.csv'
    
    # Master file paths
    MASTER_COMBOS_PATH = CLEAN_DATA_DIR / 'combo_sku_clean.csv'
    MASTER_INVENTORY_PATH = CLEAN_DATA_DIR / 'cleaned_inventory.csv'
    MASTER_MAPPING_PATH = CLEAN_DATA_DIR / 'sku_mappings_final_clean.csv'
    
    # Warehouse codes
    WAREHOUSE_COLUMNS = ['TLCQ', 'BLR7', 'BLR8', 'BOM5', 'BOM7', 'CCU1', 'CCX1', 
                        'DEL4', 'DEL5', 'DEX3', 'PNQ2', 'PNQ3', 'SDED', 'SDEE', 'XHJ9']
    
    # Default values
    DEFAULT_WAREHOUSE = 'TLCQ'
    
    # Column mappings for normalization
    COLUMN_MAPPINGS = {
        # SKU variations
        'SKU': 'sku', 'Sku': 'sku', 'sKu': 'sku', 'skU': 'sku',
        'SKU_ID': 'sku', 'sku_id': 'sku', 'Sku_Id': 'sku',
        'product_sku': 'sku', 'Product_SKU': 'sku',
        
        # MSKU variations
        'MSKU': 'msku', 'Msku': 'msku', 'mSku': 'msku', 'mskU': 'msku',
        'MASTER_SKU': 'msku', 'master_sku': 'msku', 'Master_Sku': 'msku',
        'parent_sku': 'msku', 'Parent_SKU': 'msku',
        
        # Panel/Marketplace variations
        'PANELS': 'panels', 'Panels': 'panels', 'PANEL': 'panels', 'Panel': 'panels',
        'panels': 'panels', 'panel': 'panels',
        'marketplace': 'panels', 'Marketplace': 'panels', 'MARKETPLACE': 'panels',
        'source': 'panels', 'Source': 'panels', 'SOURCE': 'panels',
        
        # Other common variations
        'DATE': 'date', 'Date': 'date',
        'QUANTITY': 'quantity', 'Quantity': 'quantity', 'qty': 'quantity', 'QTY': 'quantity',
        'WAREHOUSE': 'warehouse', 'Warehouse': 'warehouse', 'wh': 'warehouse', 'WH': 'warehouse'
    }