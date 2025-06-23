# core/management/commands/sync_to_airtable.py
from django.core.management.base import BaseCommand
from core.models import SKUMapping, Product, ComboProduct
from core.airtable_sync import airtable_sync
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sync Django data to Airtable'
    
    def add_arguments(self, parser):
        parser.add_argument('--type', type=str, 
                          choices=['all', 'sku', 'inventory', 'combo'], 
                          default='all', help='Type of data to sync')
        parser.add_argument('--limit', type=int, help='Limit records to sync')
    
    def handle(self, *args, **options):
        sync_type = options['type']
        limit = options['limit']
        
        self.stdout.write("🚀 Starting Django → Airtable sync...")
        
        if sync_type in ['all', 'sku']:
            self.sync_sku_mappings(limit)
        
        if sync_type in ['all', 'inventory']:
            self.sync_inventory(limit)
            
        if sync_type in ['all', 'combo']:
            self.sync_combo_products(limit)
        
        self.stdout.write("✅ Sync complete!")
    
    def sync_sku_mappings(self, limit=None):
        queryset = SKUMapping.objects.select_related('product', 'marketplace')
        if limit:
            queryset = queryset[:limit]
            
        self.stdout.write(f"📦 Syncing {queryset.count()} SKU mappings...")
        
        for mapping in queryset:
            try:
                airtable_sync.sync_sku_mapping_to_airtable(mapping)
                self.stdout.write(f"  ✅ {mapping.sku}")
            except Exception as e:
                self.stdout.write(f"  ❌ {mapping.sku}: {e}")
    
    def sync_inventory(self, limit=None):
        queryset = Product.objects.prefetch_related('inventory_records__warehouse')
        if limit:
            queryset = queryset[:limit]
            
        self.stdout.write(f"📊 Syncing {queryset.count()} products...")
        
        for product in queryset:
            try:
                airtable_sync.sync_product_to_airtable(product)
                self.stdout.write(f"  ✅ {product.msku}")
            except Exception as e:
                self.stdout.write(f"  ❌ {product.msku}: {e}")
    
    def sync_combo_products(self, limit=None):
        queryset = ComboProduct.objects.select_related('marketplace')
        if limit:
            queryset = queryset[:limit]
            
        self.stdout.write(f"🎁 Syncing {queryset.count()} combo products...")
        
        for combo in queryset:
            try:
                airtable_sync.sync_combo_product_to_airtable(combo)
                self.stdout.write(f"  ✅ {combo.combo_sku}")
            except Exception as e:
                self.stdout.write(f"  ❌ {combo.combo_sku}: {e}")
