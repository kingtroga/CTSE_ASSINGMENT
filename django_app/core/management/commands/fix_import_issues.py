# core/management/commands/fix_import_issues.py

import os
import csv
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction
from core.models import (
    Product, Warehouse, Inventory, Marketplace, SKUMapping, 
    ComboProduct, ComboProductItem, Order, OrderItem
)

class Command(BaseCommand):
    help = 'Fix issues that occurred during data import'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--data-path',
            type=str,
            default=getattr(settings, 'CLEAN_DATA_PATH', '../clean_data'),
            help='Path to clean data directory'
        )
        parser.add_argument(
            '--fix-skus',
            action='store_true',
            help='Fix missing SKU mappings'
        )
        parser.add_argument(
            '--fix-combos',
            action='store_true',
            help='Fix combo component linkings'
        )
        parser.add_argument(
            '--fix-models',
            action='store_true',
            help='Fix model property issues'
        )
        parser.add_argument(
            '--fix-all',
            action='store_true',
            help='Fix all identified issues'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without actually fixing'
        )
    
    def handle(self, *args, **options):
        self.data_path = options['data_path']
        self.dry_run = options['dry_run']
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 DRY RUN MODE - No changes will be made')
            )
        
        self.stdout.write(
            self.style.SUCCESS('🔧 Starting Django Import Fixes...')
        )
        
        try:
            if options['fix_all'] or options['fix_models']:
                self.fix_model_properties()
            
            if options['fix_all'] or options['fix_skus']:
                self.fix_missing_sku_mappings()
            
            if options['fix_all'] or options['fix_combos']:
                self.fix_combo_components()
            
            self.print_final_status()
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Fix process failed: {str(e)}')
            )
            raise
    
    def fix_model_properties(self):
        """Fix model property issues like remaining_quantity"""
        self.stdout.write(self.style.HTTP_INFO('\n🔧 Fixing Model Properties...'))
        
        # Check for OrderItem remaining_quantity issues
        try:
            if not self.dry_run:
                # Test the remaining_quantity property on existing OrderItems
                order_items = OrderItem.objects.all()[:5]  # Test first 5
                for item in order_items:
                    try:
                        _ = item.remaining_quantity  # This will trigger the property
                    except TypeError as e:
                        if "unsupported operand type" in str(e):
                            self.stdout.write(
                                self.style.ERROR(f'❌ remaining_quantity property still broken: {e}')
                            )
                            self.stdout.write(
                                self.style.WARNING('Please manually fix the remaining_quantity property in core/models.py')
                            )
                            return
                
                self.stdout.write('   ✅ OrderItem remaining_quantity property working correctly')
            else:
                self.stdout.write('   📝 Would test OrderItem remaining_quantity property')
                
        except Exception as e:
            self.stdout.write(f'   ⚠️  Could not test OrderItem properties: {e}')
    
    def fix_missing_sku_mappings(self):
        """Fix SKU mappings by only importing those with valid MSKUs in inventory"""
        self.stdout.write(self.style.HTTP_INFO('\n🔗 Fixing SKU Mappings (Inventory-Based)...'))
        
        # Read the SKU mappings file
        mappings_file = os.path.join(self.data_path, 'sku_mappings_final_clean.csv')
        
        if not os.path.exists(mappings_file):
            self.stdout.write(
                self.style.ERROR(f'❌ SKU mappings file not found: {mappings_file}')
            )
            return
        
        with open(mappings_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            mappings_data = list(reader)
        
        # Get existing mappings to avoid duplicates
        existing_mappings = set()
        if not self.dry_run:
            existing_mappings = set(
                SKUMapping.objects.values_list('sku', 'marketplace__code')
            )
        
        # Get ONLY MSKUs that exist in actual inventory/products
        if not self.dry_run:
            valid_inventory_mskus = set(Product.objects.values_list('msku', flat=True))
            valid_marketplaces = {mp.code: mp for mp in Marketplace.objects.all()}
        else:
            # For dry run, simulate based on known data
            valid_inventory_mskus = set()  # Will be populated from analysis
            valid_marketplaces = {}
        
        # Analyze the data first
        total_mappings = len(mappings_data)
        mapping_mskus = set()
        valid_mappings = []
        invalid_mappings = []
        
        for row in mappings_data:
            sku = row.get('sku')
            msku = row.get('msku') 
            panel = row.get('panels')
            
            if not sku or not msku or not panel:
                continue
                
            mapping_mskus.add(msku)
            
            # Check if this MSKU exists in inventory
            if not self.dry_run:
                if msku in valid_inventory_mskus:
                    valid_mappings.append(row)
                else:
                    invalid_mappings.append(row)
            else:
                # For dry run, we'll estimate based on known inventory size
                valid_mappings.append(row)
        
        # Report the analysis
        self.stdout.write(f'   📊 Total SKU mappings in file: {total_mappings}')
        self.stdout.write(f'   📊 Unique MSKUs in mappings: {len(mapping_mskus)}')
        
        if not self.dry_run:
            self.stdout.write(f'   📦 MSKUs in actual inventory: {len(valid_inventory_mskus)}')
            self.stdout.write(f'   ✅ Valid mappings (MSKU exists): {len(valid_mappings)}')
            self.stdout.write(f'   ❌ Invalid mappings (MSKU missing): {len(invalid_mappings)}')
            
            # Show some examples of missing MSKUs
            if invalid_mappings:
                missing_mskus = set(row['msku'] for row in invalid_mappings[:10])
                self.stdout.write(f'   📝 Sample missing MSKUs: {list(missing_mskus)[:5]}...')
        
        # Now import only the valid mappings
        created_count = 0
        skipped_marketplace = 0
        skipped_duplicate = 0
        
        for row in valid_mappings:
            sku = row.get('sku')
            msku = row.get('msku')
            panel = row.get('panels')
            status_1 = row.get('Status 1')
            status_2 = row.get('Status 2')
            image_url = row.get('image')
            
            # Skip if already exists
            if (sku, panel) in existing_mappings:
                skipped_duplicate += 1
                continue
            
            # Check if marketplace exists
            if not self.dry_run and panel not in valid_marketplaces:
                # Create missing marketplace
                if self.create_missing_marketplace(panel):
                    marketplace = Marketplace.objects.get(code=panel)
                    valid_marketplaces[panel] = marketplace
                else:
                    skipped_marketplace += 1
                    continue
            
            # Create the mapping (we know MSKU exists)
            if not self.dry_run:
                try:
                    product = Product.objects.get(msku=msku)
                    marketplace = valid_marketplaces[panel]
                    
                    mapping_data = {
                        'sku': sku,
                        'product': product,
                        'marketplace': marketplace,
                        'marketplace_price': None,
                        'image_url': image_url if image_url != 'NA' else None,
                        'status': status_1 if status_1 != 'NA' else 'ACTIVE',
                        'status_2': status_2 if status_2 != 'NA' else None,
                        'marketplace_product_url': None,
                    }
                    
                    mapping, created = SKUMapping.objects.get_or_create(
                        sku=sku,
                        marketplace=marketplace,
                        defaults=mapping_data
                    )
                    
                    if created:
                        created_count += 1
                        existing_mappings.add((sku, panel))
                        
                except Exception as e:
                    self.stdout.write(f'   ⚠️  Error creating mapping {sku}: {e}')
                    continue
            else:
                created_count += 1
        
        self.stdout.write(f'   ✅ Created {created_count} valid SKU mappings')
        if skipped_marketplace > 0:
            self.stdout.write(f'   ⚠️  {skipped_marketplace} skipped due to missing marketplace')
        if skipped_duplicate > 0:
            self.stdout.write(f'   ℹ️  {skipped_duplicate} skipped (already exist)')
        
        # Important business insight
        if not self.dry_run and invalid_mappings:
            self.stdout.write(
                self.style.WARNING(f'\n📝 BUSINESS INSIGHT: {len(invalid_mappings)} marketplace listings reference')
            )
            self.stdout.write(
                self.style.WARNING(f'   MSKUs that are not in current inventory (likely discontinued products)')
            )
    
    def create_missing_marketplace(self, code):
        """Create a missing marketplace with minimal data"""
        try:
            marketplace_data = {
                'code': code,
                'name': f'Marketplace {code}',
                'commission_rate': Decimal('10.00'),
                'is_active': True
            }
            
            marketplace, created = Marketplace.objects.get_or_create(
                code=code,
                defaults=marketplace_data
            )
            
            if created:
                self.stdout.write(f'   🛒 Created missing marketplace: {code}')
            
            return True
            
        except Exception as e:
            self.stdout.write(f'   ❌ Could not create marketplace {code}: {e}')
            return False
    
    def fix_combo_components(self):
        """Fix combo component linkings"""
        self.stdout.write(self.style.HTTP_INFO('\n🎁 Fixing Combo Components...'))
        
        # Read combo data
        combo_file = os.path.join(self.data_path, 'combo_sku_clean.csv')
        
        if not os.path.exists(combo_file):
            self.stdout.write(
                self.style.ERROR(f'❌ Combo file not found: {combo_file}')
            )
            return
        
        with open(combo_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            combo_data = list(reader)
        
        # Check what fields exist in the models
        if not self.dry_run:
            combo_fields = [f.name for f in ComboProduct._meta.get_fields()]
            combo_item_fields = [f.name for f in ComboProductItem._meta.get_fields()]
            self.stdout.write(f'   📋 ComboProduct fields: {combo_fields}')
            self.stdout.write(f'   📋 ComboProductItem fields: {combo_item_fields}')
        
        # Get existing combos
        if not self.dry_run:
            existing_combos = {combo.combo_sku: combo for combo in ComboProduct.objects.all()}
            existing_items = set(
                ComboProductItem.objects.values_list('combo_product__combo_sku', 'product__msku')
            )
        else:
            existing_combos = {}
            existing_items = set()
        
        created_items = 0
        
        for row in combo_data:
            combo_sku = row.get('Combo')
            status = row.get('Status')
            
            if not combo_sku or combo_sku == 'NA' or status != 'Combo':
                continue
            
            # Find the combo product
            if not self.dry_run and combo_sku not in existing_combos:
                self.stdout.write(f'   ⚠️  Combo not found: {combo_sku}')
                continue
            
            # Process component MSKUs (SKU1-SKU8)
            for i in range(1, 9):
                component_msku = row.get(f'SKU{i}')
                if component_msku and component_msku != 'NA':
                    # Skip if already exists
                    if (combo_sku, component_msku) in existing_items:
                        continue
                    
                    if not self.dry_run:
                        try:
                            combo_product = existing_combos[combo_sku]
                            component_product = Product.objects.get(msku=component_msku)
                            
                            # Only include fields that definitely exist
                            combo_item_data = {
                                'combo_product': combo_product,
                                'product': component_product,
                                'quantity': 1,
                            }
                            
                            combo_item, created = ComboProductItem.objects.get_or_create(
                                combo_product=combo_product,
                                product=component_product,
                                defaults=combo_item_data
                            )
                            
                            if created:
                                created_items += 1
                                existing_items.add((combo_sku, component_msku))
                                
                        except Product.DoesNotExist:
                            self.stdout.write(f'   ⚠️  Component product not found: {component_msku}')
                            continue
                        except Exception as e:
                            self.stdout.write(f'   ⚠️  Error linking component {component_msku}: {e}')
                            continue
                    else:
                        created_items += 1
        
        self.stdout.write(f'   ✅ Created {created_items} combo component links')
    
    def print_final_status(self):
        """Print final status after fixes"""
        self.stdout.write(self.style.SUCCESS('\n📊 FINAL STATUS AFTER FIXES:'))
        
        if not self.dry_run:
            self.stdout.write(f'   🏪 Warehouses: {Warehouse.objects.count()}')
            self.stdout.write(f'   📦 Products: {Product.objects.count()}')
            self.stdout.write(f'   🛒 Marketplaces: {Marketplace.objects.count()}')
            self.stdout.write(f'   📊 Inventory Records: {Inventory.objects.count()}')
            self.stdout.write(f'   🔗 SKU Mappings: {SKUMapping.objects.count()}')
            self.stdout.write(f'   🎁 Combo Products: {ComboProduct.objects.count()}')
            self.stdout.write(f'   📝 Combo Items: {ComboProductItem.objects.count()}')
        else:
            self.stdout.write('   📝 Dry run completed - no actual changes made')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Fix process completed!'))