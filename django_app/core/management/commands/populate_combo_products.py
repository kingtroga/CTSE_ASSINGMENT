# management/commands/populate_combo_products.py

import csv
import os
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings

# Import your models - adjust the import path based on your app structure
from core.models import Product, SKUMapping, ComboProduct, ComboProductItem, Marketplace


class Command(BaseCommand):
    help = 'Populate ComboProduct and ComboProductItem models from combo_sku_clean.csv'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-file',
            type=str,
            default='combo_sku_clean.csv',
            help='Path to the combo CSV file (default: combo_sku_clean.csv)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes to the database'
        )
        
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing combo data before importing'
        )
        
        parser.add_argument(
            '--inspect-csv',
            action='store_true',
            help='Just inspect the CSV file structure without processing'
        )
        
        parser.add_argument(
            '--data-path',
            type=str,
            default='clean_data',
            help='Directory containing the CSV files (default: clean_data)'
        )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {
            'combos_created': 0,
            'combos_updated': 0,
            'combos_skipped': 0,
            'combo_items_created': 0,
            'errors': 0,
            'warnings': 0
        }
    
    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        csv_file = options['csv_file']
        data_path = options['data_path']
        
        # Construct full path to CSV file
        if not os.path.isabs(csv_file):
            csv_file = os.path.join(data_path, csv_file)
        
        self.stdout.write(
            self.style.HTTP_INFO(f'🎁 Starting Combo Products Population...')
        )
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 DRY RUN MODE - No changes will be made to database')
            )
        
        # Check if CSV file exists
        if not os.path.exists(csv_file):
            raise CommandError(f'CSV file not found: {csv_file}')
        
        # Inspect CSV mode
        if options['inspect_csv']:
            self.inspect_csv_file(csv_file)
            return
        
        # Clear existing data if requested
        if options['clear_existing'] and not self.dry_run:
            self.clear_existing_combos()
        
        # Process the CSV file
        try:
            self.process_combo_csv(csv_file)
            self.print_final_stats()
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error processing file: {str(e)}')
            )
            raise CommandError(f'Failed to process combo data: {str(e)}')
    
    def inspect_csv_file(self, csv_file):
        """Inspect CSV file structure for debugging"""
        self.stdout.write(f'🔍 INSPECTING CSV FILE: {csv_file}')
        
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                self.stdout.write(f'\n📋 TRYING ENCODING: {encoding}')
                
                with open(csv_file, 'r', encoding=encoding) as file:
                    # Show first few lines raw
                    file.seek(0)
                    lines = [file.readline().strip() for _ in range(5)]
                    
                    self.stdout.write('📄 FIRST 5 LINES:')
                    for i, line in enumerate(lines, 1):
                        self.stdout.write(f'   Line {i}: {repr(line)[:100]}')
                    
                    # Try delimiter detection
                    file.seek(0)
                    sample = file.read(1024)
                    delimiter = self.detect_delimiter(sample)
                    
                    self.stdout.write(f'🔍 DETECTED DELIMITER: "{delimiter}" (ASCII: {ord(delimiter)})')
                    
                    # Try reading as CSV
                    file.seek(0)
                    reader = csv.DictReader(file, delimiter=delimiter)
                    
                    headers = reader.fieldnames
                    self.stdout.write(f'📊 HEADERS ({len(headers)}): {headers}')
                    
                    # Show first few rows
                    self.stdout.write('📋 SAMPLE DATA:')
                    for i, row in enumerate(reader):
                        if i >= 3:  # Show first 3 rows
                            break
                        self.stdout.write(f'   Row {i+1}: {dict(row)}')
                    
                    self.stdout.write(f'✅ ENCODING {encoding} WORKS!')
                    return
                    
            except Exception as e:
                self.stdout.write(f'❌ ENCODING {encoding} FAILED: {str(e)}')
                continue
        
        self.stdout.write('❌ NO ENCODING WORKED!')
    
    def detect_delimiter(self, sample):
        """Robust delimiter detection with fallbacks"""
        # Common delimiters to try
        delimiters = [',', ';', '\t', '|']
        
        # Method 1: Try CSV sniffer first
        try:
            sniffer = csv.Sniffer()
            detected = sniffer.sniff(sample, delimiters=',;\t|')
            return detected.delimiter
        except:
            pass
        
        # Method 2: Count occurrences of each delimiter
        delimiter_counts = {}
        for delimiter in delimiters:
            delimiter_counts[delimiter] = sample.count(delimiter)
        
        # Return the delimiter with the highest count (and > 0)
        best_delimiter = max(delimiter_counts, key=delimiter_counts.get)
        if delimiter_counts[best_delimiter] > 0:
            return best_delimiter
        
        # Method 3: Default fallback to comma
        return ','
    
    def clear_existing_combos(self):
        """Clear existing combo data"""
        self.stdout.write('🗑️  Clearing existing combo data...')
        
        deleted_items = ComboProductItem.objects.all().delete()[0]
        deleted_combos = ComboProduct.objects.all().delete()[0]
        
        self.stdout.write(
            f'   ✅ Deleted {deleted_items} combo items and {deleted_combos} combo products'
        )
    
    def process_combo_csv(self, csv_file):
        """Process the combo CSV file"""
        self.stdout.write(f'📖 Reading combo data from: {csv_file}')
        
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(csv_file, 'r', encoding=encoding) as file:
                    # Try multiple delimiter detection methods
                    sample = file.read(1024)
                    file.seek(0)
                    
                    if not sample.strip():
                        raise CommandError('CSV file appears to be empty')
                    
                    delimiter = self.detect_delimiter(sample)
                    self.stdout.write(f'   🔍 Using encoding: {encoding}, delimiter: "{delimiter}"')
                    
                    reader = csv.DictReader(file, delimiter=delimiter)
                    
                    # Read first row to check if we have data
                    try:
                        first_row = next(reader)
                        file.seek(0)
                        reader = csv.DictReader(file, delimiter=delimiter)  # Reset reader
                    except StopIteration:
                        raise CommandError('CSV file appears to be empty')
                    
                    # Validate headers (case-insensitive and flexible)
                    actual_headers = [h.strip() for h in reader.fieldnames if h]
                    required_headers = ['Combo', 'SKU1', 'SKU2', 'SKU3', 'SKU4', 'SKU5', 'SKU6', 'SKU7', 'SKU8', 'Status']
                    
                    # Check for required headers (case-insensitive)
                    header_map = {}
                    missing_headers = []
                    
                    for required in required_headers:
                        found = False
                        for actual in actual_headers:
                            if actual.lower() == required.lower():
                                header_map[required] = actual
                                found = True
                                break
                        if not found:
                            missing_headers.append(required)
                    
                    if missing_headers:
                        self.stdout.write(f'   📊 Available headers: {actual_headers}')
                        raise CommandError(f'Missing required headers: {missing_headers}')
                    
                    self.stdout.write(f'   📊 Found columns: {actual_headers}')
                    self.stdout.write(f'   ✅ All required headers present')
                    
                    # Process each row
                    row_count = 0
                    for row in reader:
                        row_count += 1
                        
                        try:
                            self.process_combo_row(row, row_count, header_map)
                        except Exception as e:
                            self.stats['errors'] += 1
                            self.stdout.write(
                                self.style.ERROR(f'   ❌ Error processing row {row_count}: {str(e)}')
                            )
                            continue
                    
                    self.stdout.write(f'   ✅ Processed {row_count} rows from CSV')
                    return  # Success, exit the encoding loop
                    
            except UnicodeDecodeError:
                continue  # Try next encoding
            except Exception as e:
                if encoding == encodings[-1]:  # Last encoding attempt
                    raise e
                continue
        
        raise CommandError('Could not read CSV file with any supported encoding')
    
    def process_combo_row(self, row, row_number, header_map=None):
        """Process a single combo row"""
        # Use header_map if provided, otherwise use direct access
        if header_map:
            combo_sku = row.get(header_map.get('Combo', 'Combo'), '').strip()
            status = row.get(header_map.get('Status', 'Status'), '').strip()
        else:
            combo_sku = row.get('Combo', '').strip()
            status = row.get('Status', '').strip()
        
        # Skip if not a combo or missing combo SKU
        if not combo_sku or status.lower() != 'combo':
            return
        
        # Get component SKUs (SKU1 through SKU8)
        component_skus = []
        for i in range(1, 9):
            sku_key = f'SKU{i}'
            if header_map:
                actual_key = header_map.get(sku_key, sku_key)
            else:
                actual_key = sku_key
                
            sku_value = row.get(actual_key, '').strip()
            if sku_value and sku_value.upper() != 'NA':
                component_skus.append(sku_value)
        
        if not component_skus:
            self.stdout.write(
                self.style.WARNING(f'   ⚠️  Row {row_number}: No component SKUs found for combo {combo_sku}')
            )
            self.stats['warnings'] += 1
            return
        
        # Process the combo
        with transaction.atomic():
            combo_product = self.create_or_update_combo(combo_sku, component_skus)
            if combo_product:
                self.create_combo_items(combo_product, component_skus, row_number)
    
    def create_or_update_combo(self, combo_sku, component_skus):
        """Create or update a ComboProduct"""
        
        # Find the marketplace for this combo SKU via SKUMapping
        marketplace = self.find_marketplace_for_sku(combo_sku)
        
        if not marketplace:
            self.stdout.write(
                self.style.WARNING(f'   ⚠️  No marketplace found for combo SKU: {combo_sku}')
            )
            self.stats['warnings'] += 1
            return None
        
        if self.dry_run:
            self.stdout.write(f'   🔍 Would create/update combo: {combo_sku} (marketplace: {marketplace.code})')
            self.stats['combos_created'] += 1
            return None
        
        # Check if combo already exists
        try:
            combo_product = ComboProduct.objects.get(combo_sku=combo_sku)
            
            # Update existing combo
            combo_product.marketplace = marketplace
            combo_product.combo_name = self.generate_combo_name(combo_sku)
            combo_product.description = f'Combo product containing {len(component_skus)} items'
            combo_product.is_active = True
            combo_product.save()
            
            # Clear existing combo items to rebuild them
            combo_product.combo_items.all().delete()
            
            self.stdout.write(f'   🔄 Updated existing combo: {combo_sku}')
            self.stats['combos_updated'] += 1
            
        except ComboProduct.DoesNotExist:
            # Create new combo
            combo_product = ComboProduct.objects.create(
                combo_sku=combo_sku,
                combo_name=self.generate_combo_name(combo_sku),
                marketplace=marketplace,
                combo_price=Decimal('0.00'),  # Will be updated later if needed
                description=f'Combo product containing {len(component_skus)} items',
                is_active=True,
                is_auto_split=True
            )
            
            self.stdout.write(f'   ✅ Created new combo: {combo_sku}')
            self.stats['combos_created'] += 1
        
        return combo_product
    
    def create_combo_items(self, combo_product, component_skus, row_number):
        """Create ComboProductItem records for the combo"""
        
        if self.dry_run:
            self.stdout.write(f'   🔍 Would create {len(component_skus)} combo items for {combo_product.combo_sku if combo_product else "combo"}')
            self.stats['combo_items_created'] += len(component_skus)
            return
        
        sort_order = 10  # Start at 10, increment by 10 for each item
        
        for component_sku in component_skus:
            # Find the product for this component SKU
            product = self.find_product_for_sku(component_sku)
            
            if not product:
                self.stdout.write(
                    self.style.WARNING(f'   ⚠️  Row {row_number}: Product not found for component SKU: {component_sku}')
                )
                self.stats['warnings'] += 1
                continue
            
            # Create combo item
            try:
                combo_item, created = ComboProductItem.objects.get_or_create(
                    combo_product=combo_product,
                    product=product,
                    defaults={
                        'quantity': 1,  # Default quantity
                        'sort_order': sort_order,
                        'is_required': True,
                        'item_note': f'Component from SKU: {component_sku}'
                    }
                )
                
                if created:
                    self.stats['combo_items_created'] += 1
                    self.stdout.write(f'     ➕ Added component: {component_sku} → {product.msku}')
                else:
                    # Update existing item
                    combo_item.sort_order = sort_order
                    combo_item.save()
                    self.stdout.write(f'     🔄 Updated component: {component_sku} → {product.msku}')
                
                sort_order += 10
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'     ❌ Error creating combo item for {component_sku}: {str(e)}')
                )
                self.stats['errors'] += 1
    
    def find_marketplace_for_sku(self, sku):
        """Find marketplace for a SKU via SKUMapping"""
        try:
            # Look for SKU mapping
            sku_mapping = SKUMapping.objects.filter(sku=sku).first()
            if sku_mapping:
                return sku_mapping.marketplace
            
            # If no direct mapping, try to infer from SKU prefix
            # This is based on your marketplace naming patterns
            if sku.startswith('CSTE_'):
                # Try to find a CSTE marketplace
                marketplace = Marketplace.objects.filter(code__icontains='CSTE').first()
                if marketplace:
                    return marketplace
            
            # Default to first available marketplace
            return Marketplace.objects.first()
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'   ⚠️  Error finding marketplace for {sku}: {str(e)}')
            )
            return None
    
    def find_product_for_sku(self, sku):
        """Find Product via SKU mapping"""
        try:
            # Method 1: Direct SKUMapping lookup
            sku_mapping = SKUMapping.objects.filter(sku=sku).first()
            if sku_mapping:
                return sku_mapping.product
            
            # Method 2: Direct MSKU lookup (if the SKU is actually an MSKU)
            try:
                product = Product.objects.get(msku=sku)
                return product
            except Product.DoesNotExist:
                pass
            
            # Method 3: Try case-insensitive lookup
            sku_mapping = SKUMapping.objects.filter(sku__iexact=sku).first()
            if sku_mapping:
                return sku_mapping.product
            
            return None
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'   ⚠️  Error finding product for SKU {sku}: {str(e)}')
            )
            return None
    
    def generate_combo_name(self, combo_sku):
        """Generate a human-readable name for the combo"""
        # Remove prefixes and clean up the name
        name = combo_sku.replace('CSTE_', '').replace('_', ' ')
        
        # Capitalize words
        name_parts = name.split()
        cleaned_parts = []
        
        for part in name_parts:
            # Skip numeric prefixes
            if part.isdigit():
                continue
            # Clean up common abbreviations
            if part.lower() in ['ot', 'sg', 'mb', 'st', 'hd']:
                continue
            cleaned_parts.append(part.capitalize())
        
        if cleaned_parts:
            return ' '.join(cleaned_parts)
        else:
            return combo_sku  # Fallback to original SKU
    
    def print_final_stats(self):
        """Print final statistics"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('🎁 COMBO PRODUCTS POPULATION COMPLETED'))
        self.stdout.write('='*60)
        
        self.stdout.write(f'📊 STATISTICS:')
        self.stdout.write(f'   ✅ Combos Created: {self.stats["combos_created"]}')
        self.stdout.write(f'   🔄 Combos Updated: {self.stats["combos_updated"]}')
        self.stdout.write(f'   ⏭️  Combos Skipped: {self.stats["combos_skipped"]}')
        self.stdout.write(f'   ➕ Combo Items Created: {self.stats["combo_items_created"]}')
        self.stdout.write(f'   ⚠️  Warnings: {self.stats["warnings"]}')
        self.stdout.write(f'   ❌ Errors: {self.stats["errors"]}')
        
        # Final database counts
        if not self.dry_run:
            total_combos = ComboProduct.objects.count()
            total_combo_items = ComboProductItem.objects.count()
            active_combos = ComboProduct.objects.filter(is_active=True).count()
            
            self.stdout.write(f'\n📊 FINAL DATABASE STATUS:')
            self.stdout.write(f'   🎁 Total Combo Products: {total_combos}')
            self.stdout.write(f'   📦 Total Combo Items: {total_combo_items}')
            self.stdout.write(f'   ✅ Active Combos: {active_combos}')
            
            # Sample combo for verification
            sample_combo = ComboProduct.objects.first()
            if sample_combo:
                self.stdout.write(f'\n🔍 SAMPLE COMBO:')
                self.stdout.write(f'   Combo SKU: {sample_combo.combo_sku}')
                self.stdout.write(f'   Name: {sample_combo.combo_name}')
                self.stdout.write(f'   Marketplace: {sample_combo.marketplace.code}')
                self.stdout.write(f'   Components: {sample_combo.total_items}')
                
                # Show components
                for item in sample_combo.combo_items.all()[:3]:  # Show first 3
                    self.stdout.write(f'     - {item.product.msku} (×{item.quantity})')
                
                if sample_combo.total_items > 3:
                    self.stdout.write(f'     ... and {sample_combo.total_items - 3} more')
        
        if self.stats['errors'] > 0:
            self.stdout.write(
                self.style.WARNING(f'\n⚠️  {self.stats["errors"]} errors occurred during processing. Check the output above for details.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\n🎉 All combo products processed successfully!')
            )


# Optional: Add a separate command for validation
class ComboValidationCommand(BaseCommand):
    """Validate combo data integrity"""
    help = 'Validate combo products and their components'
    
    def handle(self, *args, **options):
        self.stdout.write('🔍 Validating combo data integrity...')
        
        issues = []
        
        # Check for combos without items
        empty_combos = ComboProduct.objects.filter(combo_items__isnull=True)
        if empty_combos.exists():
            issues.append(f'Found {empty_combos.count()} combos without any items')
        
        # Check for combo items with inactive products
        inactive_items = ComboProductItem.objects.filter(product__is_active=False)
        if inactive_items.exists():
            issues.append(f'Found {inactive_items.count()} combo items with inactive products')
        
        # Check for combos without marketplace
        no_marketplace = ComboProduct.objects.filter(marketplace__isnull=True)
        if no_marketplace.exists():
            issues.append(f'Found {no_marketplace.count()} combos without marketplace')
        
        if issues:
            self.stdout.write(self.style.WARNING('⚠️  Issues found:'))
            for issue in issues:
                self.stdout.write(f'   - {issue}')
        else:
            self.stdout.write(self.style.SUCCESS('✅ All combo data looks good!'))
        
        # Summary stats
        total_combos = ComboProduct.objects.count()
        total_items = ComboProductItem.objects.count()
        avg_items = total_items / total_combos if total_combos > 0 else 0
        
        self.stdout.write(f'\n📊 SUMMARY:')
        self.stdout.write(f'   Total Combos: {total_combos}')
        self.stdout.write(f'   Total Items: {total_items}')
        self.stdout.write(f'   Average Items per Combo: {avg_items:.1f}')