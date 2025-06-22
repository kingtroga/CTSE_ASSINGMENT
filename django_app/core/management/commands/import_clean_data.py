# core/management/commands/import_clean_data.py

import os
import csv
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction
from core.models import (
    Product, Warehouse, Inventory, Marketplace, SKUMapping, 
    ComboProduct, ComboProductItem
)

class Command(BaseCommand):
    help = 'Import clean CSV data into Django models'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--data-path',
            type=str,
            default=getattr(settings, 'CLEAN_DATA_PATH', '../clean_data'),
            help='Path to clean data directory'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip records that already exist'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )
    
    def handle(self, *args, **options):
        self.data_path = options['data_path']
        self.skip_existing = options['skip_existing']
        self.dry_run = options['dry_run']
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 DRY RUN MODE - No data will be imported')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'📂 Reading clean data from: {self.data_path}')
        )
        
        # Check if clean data directory exists
        if not os.path.exists(self.data_path):
            raise CommandError(f'Clean data directory not found: {self.data_path}')
        
        # Import data in dependency order
        try:
            with transaction.atomic():
                self.import_warehouses()
                self.import_products()
                self.import_marketplaces()
                self.import_inventory()
                self.import_sku_mappings()
                self.import_combo_products()
                
                if self.dry_run:
                    self.stdout.write(
                        self.style.WARNING('🔄 Rolling back transaction (dry run)')
                    )
                    raise Exception("Dry run - rolling back")
                    
        except Exception as e:
            if not self.dry_run:
                self.stdout.write(
                    self.style.ERROR(f'❌ Import failed: {str(e)}')
                )
                raise
        
        if not self.dry_run:
            self.stdout.write(
                self.style.SUCCESS('✅ All data imported successfully!')
            )
        
        self.print_summary()
    
    def read_csv_file(self, filename):
        """Read CSV file and return data"""
        filepath = os.path.join(self.data_path, filename)
        
        if not os.path.exists(filepath):
            self.stdout.write(
                self.style.WARNING(f'⚠️  File not found: {filename} - Skipping')
            )
            return []
        
        self.stdout.write(f'📖 Reading {filename}...')
        
        with open(filepath, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            data = list(reader)
            
        self.stdout.write(f'   📊 Found {len(data)} rows')
        return data
    
    def import_warehouses(self):
        """Import warehouse data from cleaned_inventory.csv column headers"""
        self.stdout.write(self.style.HTTP_INFO('\n🏪 Importing Warehouses from inventory columns...'))
        
        # Read inventory file to get warehouse codes from column headers
        inventory_data = self.read_csv_file('cleaned_inventory.csv')
        
        if not inventory_data:
            self.stdout.write(
                self.style.ERROR('❌ cleaned_inventory.csv not found! Cannot extract warehouse codes.')
            )
            return
        
        # Extract warehouse codes from column headers (excluding non-warehouse columns)
        if inventory_data:
            all_columns = list(inventory_data[0].keys())
            warehouse_columns = [col for col in all_columns 
                               if col not in ['Product Name', 'msku', 'Opening Stock', 'Buffer Stock']]
            
            self.stdout.write(f'   📍 Found warehouse columns: {warehouse_columns}')
        
        # Create warehouse records - using only basic fields that definitely exist
        created_count = 0
        for warehouse_code in warehouse_columns:
            warehouse_data = {
                'code': warehouse_code,
                'name': f'{warehouse_code} Warehouse',
                # Only include fields that definitely exist in the model
            }
            
            if not self.dry_run:
                warehouse, created = Warehouse.objects.get_or_create(
                    code=warehouse_code,
                    defaults=warehouse_data
                )
                if created or not self.skip_existing:
                    created_count += 1
            else:
                created_count += 1
        
        self.stdout.write(f'   ✅ Processed {created_count} warehouses')
    
    def import_products(self):
        """Import product data from cleaned_inventory.csv"""
        self.stdout.write(self.style.HTTP_INFO('\n📦 Importing Products from cleaned_inventory.csv...'))
        
        # Products are in the inventory file
        products_data = self.read_csv_file('cleaned_inventory.csv')
        
        if not products_data:
            self.stdout.write(
                self.style.ERROR('❌ cleaned_inventory.csv not found! This file contains products.')
            )
            return
        
        created_count = 0
        for row in products_data:
            # Extract product data from inventory CSV
            product_data = {
                'msku': row.get('msku'),
                'product_name': row.get('Product Name'),
                'category': None,  # Not in this CSV
                'brand': None,     # Not in this CSV
                'cost_price': None,  # Not in this CSV
                'is_active': True  # Assume active if in inventory
            }
            
            # Skip if no MSKU or Product Name
            if not product_data['msku'] or not product_data['product_name']:
                continue
            
            if not self.dry_run:
                product, created = Product.objects.get_or_create(
                    msku=product_data['msku'],
                    defaults=product_data
                )
                if created or not self.skip_existing:
                    created_count += 1
            else:
                created_count += 1
        
        self.stdout.write(f'   ✅ Processed {created_count} products')
    
    def import_marketplaces(self):
        """Import marketplace data based on panels in SKU mappings"""
        self.stdout.write(self.style.HTTP_INFO('\n🛒 Importing Marketplaces...'))
        
        # Your exact marketplace codes from the SKU mappings data
        marketplaces_data = [
            {'code': 'CSTE AMAZON', 'name': 'CSTE Amazon', 'commission_rate': Decimal('15.00')},
            {'code': 'CSTE FK', 'name': 'CSTE Flipkart', 'commission_rate': Decimal('12.00')},
            {'code': 'CSTE MEESHO', 'name': 'CSTE Meesho', 'commission_rate': Decimal('8.00')},
            {'code': 'GL FK', 'name': 'GL Flipkart', 'commission_rate': Decimal('12.00')},
            {'code': 'Rudrav Meesho', 'name': 'Rudrav Meesho', 'commission_rate': Decimal('8.00')},
            {'code': 'MISC', 'name': 'Miscellaneous', 'commission_rate': Decimal('10.00')},
        ]
        
        created_count = 0
        for marketplace_data in marketplaces_data:
            if not self.dry_run:
                marketplace, created = Marketplace.objects.get_or_create(
                    code=marketplace_data['code'],
                    defaults=marketplace_data
                )
                if created or not self.skip_existing:
                    created_count += 1
            else:
                created_count += 1
        
        self.stdout.write(f'   ✅ Processed {created_count} marketplaces')
    
    def import_inventory(self):
        """Import inventory data from cleaned_inventory.csv"""
        self.stdout.write(self.style.HTTP_INFO('\n📊 Importing Inventory from cleaned_inventory.csv...'))
        
        inventory_data = self.read_csv_file('cleaned_inventory.csv')
        
        if not inventory_data:
            self.stdout.write(
                self.style.ERROR('❌ cleaned_inventory.csv not found!')
            )
            return
        
        # Get warehouse columns (exclude non-warehouse columns)
        if inventory_data:
            all_columns = list(inventory_data[0].keys())
            warehouse_columns = [col for col in all_columns 
                               if col not in ['Product Name', 'msku', 'Opening Stock', 'Buffer Stock']]
        
        created_count = 0
        for row in inventory_data:
            msku = row.get('msku')
            
            if not msku:
                continue
            
            try:
                product = Product.objects.get(msku=msku)
                
                # Create inventory record for each warehouse
                for warehouse_code in warehouse_columns:
                    stock_value = row.get(warehouse_code, '0')
                    current_stock = self.safe_int(stock_value) or 0
                    
                    try:
                        warehouse = Warehouse.objects.get(code=warehouse_code)
                        
                        inventory_data_obj = {
                            'product': product,
                            'warehouse': warehouse,
                            'current_stock': current_stock,
                            # Only include fields that definitely exist in the model
                        }
                        
                        if not self.dry_run:
                            inventory, created = Inventory.objects.get_or_create(
                                product=product,
                                warehouse=warehouse,
                                defaults=inventory_data_obj
                            )
                            if created or not self.skip_existing:
                                created_count += 1
                        else:
                            created_count += 1
                            
                    except Warehouse.DoesNotExist:
                        continue
                        
            except Product.DoesNotExist:
                continue
        
        self.stdout.write(f'   ✅ Processed {created_count} inventory records')
    
    def create_default_inventory(self):
        """Create default inventory records for all products in all warehouses"""
        if self.dry_run:
            product_count = Product.objects.count()
            warehouse_count = Warehouse.objects.count()
            total_records = product_count * warehouse_count
            self.stdout.write(f'   📝 Would create {total_records} default inventory records')
            return
        
        created_count = 0
        for product in Product.objects.all():
            for warehouse in Warehouse.objects.all():
                inventory, created = Inventory.objects.get_or_create(
                    product=product,
                    warehouse=warehouse,
                    defaults={
                        'current_stock': 0,
                        # Only include basic fields that exist
                    }
                )
                if created:
                    created_count += 1
        
        self.stdout.write(f'   ✅ Created {created_count} default inventory records')
    
    def import_sku_mappings(self):
        """Import SKU mapping data from sku_mappings_final_clean.csv - Your critical 5,115 mappings!"""
        self.stdout.write(self.style.HTTP_INFO('\n🔗 Importing SKU Mappings from sku_mappings_final_clean.csv...'))
        
        mappings_data = self.read_csv_file('sku_mappings_final_clean.csv')
        
        if not mappings_data:
            self.stdout.write(
                self.style.ERROR('❌ sku_mappings_final_clean.csv not found! This contains your 5,115 critical mappings.')
            )
            return
        
        created_count = 0
        error_count = 0
        
        for row in mappings_data:
            # Use exact column names from your CSV
            sku = row.get('sku')
            msku = row.get('msku') 
            panel = row.get('panels')  # Note: 'panels' not 'panel'
            status_1 = row.get('Status 1')
            status_2 = row.get('Status 2')
            image_url = row.get('image')
            
            if not sku or not msku or not panel:
                error_count += 1
                continue
            
            try:
                product = Product.objects.get(msku=msku)
                marketplace = Marketplace.objects.get(code=panel)
                
                mapping_data = {
                    'sku': sku,
                    'product': product,
                    'marketplace': marketplace,
                    'marketplace_price': None,  # Not in this CSV
                    'image_url': image_url if image_url != 'NA' else None,
                    'status': status_1 if status_1 != 'NA' else 'ACTIVE',
                    'status_2': status_2 if status_2 != 'NA' else None,
                    'marketplace_product_url': None,  # Not in this CSV
                }
                
                if not self.dry_run:
                    mapping, created = SKUMapping.objects.get_or_create(
                        sku=sku,
                        marketplace=marketplace,
                        defaults=mapping_data
                    )
                    if created or not self.skip_existing:
                        created_count += 1
                else:
                    created_count += 1
                    
            except (Product.DoesNotExist, Marketplace.DoesNotExist):
                error_count += 1
                continue
        
        self.stdout.write(f'   ✅ Processed {created_count} SKU mappings')
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(f'   ⚠️  {error_count} mappings skipped due to missing references')
            )
    
    def import_combo_products(self):
        """Import combo product data from combo_sku_clean.csv"""
        self.stdout.write(self.style.HTTP_INFO('\n🎁 Importing Combo Products from combo_sku_clean.csv...'))
        
        combo_data = self.read_csv_file('combo_sku_clean.csv')
        
        if not combo_data:
            self.stdout.write(
                self.style.WARNING('⚠️  combo_sku_clean.csv not found. Skipping combos.')
            )
            return
        
        created_combos = 0
        created_items = 0
        
        for row in combo_data:
            combo_sku = row.get('Combo')
            status = row.get('Status')
            
            if not combo_sku or combo_sku == 'NA':
                continue
            
            # Try to extract marketplace from combo SKU (e.g., "CSTE_034" -> "CSTE")
            marketplace_code = None
            if '_' in combo_sku:
                marketplace_prefix = combo_sku.split('_')[0]
                # Map prefixes to your actual marketplace codes
                marketplace_mapping = {
                    'CSTE': 'CSTE AMAZON',  # Default CSTE to Amazon
                    'ST-BTS': 'MISC',       # Custom combos
                    'Minecraft': 'MISC',    # Gaming combos
                }
                marketplace_code = marketplace_mapping.get(marketplace_prefix, 'MISC')
            else:
                marketplace_code = 'MISC'
            
            try:
                marketplace = Marketplace.objects.get(code=marketplace_code)
                
                combo_data_obj = {
                    'combo_sku': combo_sku,
                    'combo_name': combo_sku,  # Use SKU as name since we don't have a separate name
                    'marketplace': marketplace,
                    'combo_price': Decimal('0.00'),  # We don't have price data
                    'description': f'Combo product: {combo_sku}',
                    'combo_image_url': None,  # Not in this CSV
                    'is_active': status == 'Combo',  # Active if status is 'Combo'
                }
                
                if not self.dry_run:
                    combo, created = ComboProduct.objects.get_or_create(
                        combo_sku=combo_sku,
                        defaults=combo_data_obj
                    )
                    if created or not self.skip_existing:
                        created_combos += 1
                        
                        # Now add component SKUs (SKU1 through SKU8)
                        for i in range(1, 9):  # SKU1 to SKU8
                            component_sku = row.get(f'SKU{i}')
                            if component_sku and component_sku != 'NA':
                                try:
                                    # Find the SKU mapping for this component
                                    sku_mapping = SKUMapping.objects.filter(sku=component_sku).first()
                                    if sku_mapping:
                                        combo_item_data = {
                                            'combo_product': combo,
                                            'product': sku_mapping.product,
                                            'quantity': 1,  # Default quantity
                                            'is_active': True,
                                        }
                                        
                                        combo_item, item_created = ComboProductItem.objects.get_or_create(
                                            combo_product=combo,
                                            product=sku_mapping.product,
                                            defaults=combo_item_data
                                        )
                                        if item_created:
                                            created_items += 1
                                            
                                except Exception:
                                    continue  # Skip if component SKU not found
                else:
                    created_combos += 1
                    # In dry run, estimate component items
                    component_count = sum(1 for i in range(1, 9) 
                                        if row.get(f'SKU{i}') and row.get(f'SKU{i}') != 'NA')
                    created_items += component_count
                    
            except Marketplace.DoesNotExist:
                continue
        
        self.stdout.write(f'   ✅ Processed {created_combos} combo products')
        self.stdout.write(f'   ✅ Processed {created_items} combo component items')
    
    def safe_decimal(self, value):
        """Safely convert to Decimal"""
        if not value or value == '':
            return None
        try:
            return Decimal(str(value).replace(',', '').replace('₹', '').strip())
        except:
            return None
    
    def safe_int(self, value):
        """Safely convert to int"""
        if not value or value == '':
            return None
        try:
            return int(float(str(value).replace(',', '')))
        except:
            return None
    
    def safe_boolean(self, value, default=False):
        """Safely convert to boolean"""
        if value is None or value == '':
            return default
        if isinstance(value, bool):
            return value
        return str(value).lower() in ['true', '1', 'yes', 'active', 'y']
    
    def print_summary(self):
        """Print import summary"""
        self.stdout.write(self.style.SUCCESS('\n📊 IMPORT SUMMARY:'))
        self.stdout.write(f'   🏪 Warehouses: {Warehouse.objects.count()}')
        self.stdout.write(f'   📦 Products: {Product.objects.count()}')
        self.stdout.write(f'   🛒 Marketplaces: {Marketplace.objects.count()}')
        self.stdout.write(f'   📊 Inventory Records: {Inventory.objects.count()}')
        self.stdout.write(f'   🔗 SKU Mappings: {SKUMapping.objects.count()}')
        self.stdout.write(f'   🎁 Combo Products: {ComboProduct.objects.count()}')
        self.stdout.write(f'   📝 Combo Items: {ComboProductItem.objects.count()}')