# requirements.txt - Add these dependencies
"""
requests>=2.31.0
python-decouple>=3.8
"""

# =============================================================================
# DJANGO SETTINGS CONFIGURATION
# =============================================================================

# settings.py - Add to your Django settings
import os
from decouple import config

# Airtable Configuration
AIRTABLE_BASE_ID = config('AIRTABLE_BASE_ID', default='appLt31NqOLXcv3V1')
AIRTABLE_PERSONAL_ACCESS_TOKEN = config('AIRTABLE_PERSONAL_ACCESS_TOKEN', 
    default='patRWURHXsrBYtayJ.0715b57665e5e586019b4c2b820243ecfb73ca041126b2c7d774521f9d6b9d41')
AIRTABLE_WEBHOOK_SECRET = config('AIRTABLE_WEBHOOK_SECRET', 
    default='wh_secret_2024_django_airtable_sync_x9k2m5n8p1q4r7t0')

# Airtable Table Configuration (matches your exact setup)
AIRTABLE_TABLES = {
    'sku_mappings': 'SKU_Mappings',        # tbl0c8O7MWVIRrm96
    'combo_products': 'Combo_Products',    # tblu0dzhsY7CgW3Qn  
    'inventory': 'Inventory'               # tbl2LVelu8mpV6Vkr
}

# =============================================================================
# AIRTABLE SYNC SERVICE (core/airtable_sync.py)
# =============================================================================

import requests
import json
import logging
from django.conf import settings
from django.db.models import Q
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class AirtableSync:
    """Main service for syncing data between Django and Airtable"""
    
    def __init__(self):
        self.base_id = settings.AIRTABLE_BASE_ID
        self.access_token = settings.AIRTABLE_PERSONAL_ACCESS_TOKEN
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        # Test connection on initialization
        self._validate_connection()
    
    def _validate_connection(self):
        """Validate Airtable connection"""
        try:
            url = f"https://api.airtable.com/v0/meta/bases/{self.base_id}/tables"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                logger.info("✅ Airtable connection validated successfully")
                return True
            else:
                logger.error(f"❌ Airtable connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"💥 Airtable connection error: {e}")
            return False
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make authenticated request to Airtable API"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            elif method == 'PATCH':
                response = requests.patch(url, headers=self.headers, json=data)
            elif method == 'DELETE':
                response = requests.delete(url, headers=self.headers)
            
            # Handle common errors
            if response.status_code == 401:
                raise Exception("Authentication failed - check your access token")
            elif response.status_code == 403:
                raise Exception("Permission denied - token may lack required scopes")
            elif response.status_code == 404:
                raise Exception("Resource not found - check table/record IDs")
            elif response.status_code == 422:
                error_details = response.json().get('error', {})
                raise Exception(f"Validation error: {error_details.get('message', 'Unknown error')}")
            elif response.status_code == 429:
                raise Exception("Rate limit exceeded - please wait before retrying")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Airtable API error: {e}")
            raise
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def find_record_by_field(self, table_name: str, field_name: str, value: str) -> Optional[str]:
        """Find Airtable record ID by field value"""
        try:
            # Escape special characters in the value for Airtable formula
            escaped_value = value.replace("'", "\\'").replace("#", "\\#").replace('"', '\\"')
            formula = f"{{{field_name}}}='{escaped_value}'"
            
            # URL encode the entire filter formula
            import urllib.parse
            encoded_formula = urllib.parse.quote(formula)
            endpoint = f"{table_name}?filterByFormula={encoded_formula}"
            
            result = self._make_request('GET', endpoint)
            records = result.get('records', [])
            
            return records[0]['id'] if records else None
            
        except Exception as e:
            logger.error(f"Error finding record by {field_name}={value}: {e}")
            return None
    
    def create_or_update_record(self, table_name: str, lookup_field: str, lookup_value: str, fields: Dict) -> str:
        """Create new record or update existing one"""
        existing_id = self.find_record_by_field(table_name, lookup_field, lookup_value)
        
        if existing_id:
            # Update existing record
            data = {"fields": fields}
            self._make_request('PATCH', f"{table_name}/{existing_id}", data)
            return existing_id
        else:
            # Create new record
            data = {"fields": fields}
            result = self._make_request('POST', table_name, data)
            return result['id']
    
    # =============================================================================
    # SKU MAPPINGS SYNC (Django → Airtable)
    # =============================================================================
    
    def sync_sku_mapping_to_airtable(self, sku_mapping):
        """Sync SKU mapping from Django to Airtable"""
        try:
            # Prepare fields for Airtable (matching your exact column names)
            fields = {
                'sku': sku_mapping.sku,
                'msku': sku_mapping.product.msku if sku_mapping.product else '',
                'marketplace': sku_mapping.marketplace.code if sku_mapping.marketplace else '',
                'status': sku_mapping.status,
                'status_2': sku_mapping.status_2 or '',
                'marketplace_price': float(sku_mapping.marketplace_price) if sku_mapping.marketplace_price else 0,
                'image_url': sku_mapping.image_url or '',
                'marketplace_product_url': sku_mapping.marketplace_product_url or '',
                'django_id': f"{sku_mapping.sku}_{sku_mapping.marketplace.code}"  # Composite key
            }
            
            # Use django_id as lookup field for updates
            record_id = self.create_or_update_record(
                settings.AIRTABLE_TABLES['sku_mappings'],
                'django_id',
                fields['django_id'],
                fields
            )
            
            logger.info(f"✅ Synced SKU mapping {sku_mapping.sku} to Airtable")
            return record_id
            
        except Exception as e:
            logger.error(f"❌ Failed to sync SKU mapping {sku_mapping.sku}: {e}")
            raise
    
    # =============================================================================
    # INVENTORY SYNC (Django → Airtable)
    # =============================================================================
    
    def sync_product_to_airtable(self, product):
        """Sync product inventory from Django to Airtable"""
        try:
            # Get stock levels for all warehouses
            warehouse_codes = ['TLCQ', 'BLR7', 'BLR8', 'BOM5', 'BOM7', 'CCU1', 'CCX1', 
                              'DEL4', 'DEL5', 'DEX3', 'PNQ2', 'PNQ3', 'SDED', 'SDEE', 'XHJ9']
            
            # Prepare fields for Airtable
            fields = {
                'msku': product.msku,
                'product_name': product.product_name,
                'last_updated': datetime.now().isoformat()
            }
            
            # Add warehouse stock levels
            for warehouse_code in warehouse_codes:
                try:
                    inventory_record = product.inventory_records.filter(
                        warehouse__code=warehouse_code
                    ).first()
                    
                    # Use current_stock if available, otherwise 0
                    stock_level = inventory_record.current_stock if inventory_record else 0
                    fields[warehouse_code] = stock_level
                    
                except Exception as e:
                    logger.warning(f"Error getting stock for {product.msku} at {warehouse_code}: {e}")
                    fields[warehouse_code] = 0
            
            # Use msku as lookup field
            record_id = self.create_or_update_record(
                settings.AIRTABLE_TABLES['inventory'],
                'msku',
                product.msku,
                fields
            )
            
            logger.info(f"✅ Synced inventory for {product.msku} to Airtable")
            return record_id
            
        except Exception as e:
            logger.error(f"❌ Failed to sync inventory for {product.msku}: {e}")
            raise
    
    # =============================================================================
    # COMBO PRODUCTS SYNC (Django → Airtable)
    # =============================================================================
    
    def sync_combo_product_to_airtable(self, combo_product):
        """Sync combo product from Django to Airtable"""
        try:
            # Prepare fields for Airtable (matching your exact column names)
            fields = {
                'combo_sku': combo_product.combo_sku,
                'combo_name': combo_product.combo_name,
                'status': 'ACTIVE' if combo_product.is_active else 'INACTIVE',
                'combo_price': float(combo_product.combo_price),
                'is_auto_split': combo_product.is_auto_split,
                'total_items': combo_product.total_items,  # Uses your property
                'description': combo_product.description or '',
                'combo_image_url': combo_product.combo_image_url or '',
                'marketplace': combo_product.marketplace.code if combo_product.marketplace else ''
            }
            
            # Use combo_sku as lookup field
            record_id = self.create_or_update_record(
                settings.AIRTABLE_TABLES['combo_products'],
                'combo_sku',
                combo_product.combo_sku,
                fields
            )
            
            logger.info(f"✅ Synced combo product {combo_product.combo_sku} to Airtable")
            return record_id
            
        except Exception as e:
            logger.error(f"❌ Failed to sync combo product {combo_product.combo_sku}: {e}")
            raise
    
    # =============================================================================
    # AIRTABLE → DJANGO SYNC METHODS
    # =============================================================================
    
    def sync_sku_mapping_from_airtable(self, record_data: Dict):
        """Sync SKU mapping from Airtable to Django"""
        from .models import SKUMapping, Product, Marketplace
        
        try:
            fields = record_data.get('fields', {})
            
            # Get required fields
            sku = fields.get('sku')
            msku = fields.get('msku')
            marketplace_code = fields.get('marketplace')
            
            if not all([sku, msku, marketplace_code]):
                logger.warning("Missing required fields in Airtable record")
                return
            
            # Get Django objects
            try:
                product = Product.objects.get(msku=msku)
                marketplace = Marketplace.objects.get(code=marketplace_code)
            except (Product.DoesNotExist, Marketplace.DoesNotExist) as e:
                logger.error(f"Django object not found: {e}")
                return
            
            # Create or update SKU mapping
            sku_mapping, created = SKUMapping.objects.update_or_create(
                sku=sku,
                marketplace=marketplace,
                defaults={
                    'product': product,
                    'status': fields.get('status', 'ACTIVE'),
                    'status_2': fields.get('status_2', ''),
                    'marketplace_price': fields.get('marketplace_price', 0),
                    'image_url': fields.get('image_url', ''),
                    'marketplace_product_url': fields.get('marketplace_product_url', '')
                }
            )
            
            action = "Created" if created else "Updated"
            logger.info(f"✅ {action} SKU mapping {sku} from Airtable")
            
        except Exception as e:
            logger.error(f"❌ Failed to sync SKU mapping from Airtable: {e}")
    
    def sync_inventory_from_airtable(self, record_data: Dict):
        """Sync inventory from Airtable to Django"""
        from .models import Product, Warehouse, Inventory, InventoryMovement
        
        try:
            fields = record_data.get('fields', {})
            msku = fields.get('msku')
            
            if not msku:
                logger.warning("Missing msku in Airtable inventory record")
                return
            
            # Get product
            try:
                product = Product.objects.get(msku=msku)
            except Product.DoesNotExist:
                logger.error(f"Product {msku} not found in Django")
                return
            
            # Update warehouse stocks
            warehouse_codes = ['TLCQ', 'BLR7', 'BLR8', 'BOM5', 'BOM7', 'CCU1', 'CCX1', 
                              'DEL4', 'DEL5', 'DEX3', 'PNQ2', 'PNQ3', 'SDED', 'SDEE', 'XHJ9']
            
            for warehouse_code in warehouse_codes:
                if warehouse_code in fields:
                    try:
                        warehouse = Warehouse.objects.get(code=warehouse_code)
                        new_stock = int(fields[warehouse_code] or 0)
                        
                        # Get or create inventory record
                        inventory, created = Inventory.objects.get_or_create(
                            product=product,
                            warehouse=warehouse,
                            defaults={'current_stock': new_stock}
                        )
                        
                        # Update stock if changed
                        if inventory.current_stock != new_stock:
                            old_stock = inventory.current_stock
                            quantity_change = new_stock - old_stock
                            
                            # Create inventory movement record
                            InventoryMovement.objects.create(
                                movement_type='ADJUSTMENT_POSITIVE' if quantity_change > 0 else 'ADJUSTMENT_NEGATIVE',
                                product=product,
                                warehouse=warehouse,
                                quantity=quantity_change,
                                stock_before=old_stock,
                                stock_after=new_stock,
                                reason="Updated from Airtable"
                            )
                            
                            # Update inventory
                            inventory.current_stock = new_stock
                            inventory.save()
                            
                            logger.info(f"✅ Updated {msku} stock at {warehouse_code}: {old_stock} → {new_stock}")
                    
                    except Exception as e:
                        logger.error(f"Error updating {warehouse_code} stock: {e}")
            
        except Exception as e:
            logger.error(f"❌ Failed to sync inventory from Airtable: {e}")
    
    def sync_combo_product_from_airtable(self, record_data: Dict):
        """Sync combo product from Airtable to Django"""
        from .models import ComboProduct, Marketplace
        
        try:
            fields = record_data.get('fields', {})
            combo_sku = fields.get('combo_sku')
            marketplace_code = fields.get('marketplace')
            
            if not all([combo_sku, marketplace_code]):
                logger.warning("Missing required fields in Airtable combo record")
                return
            
            # Get marketplace
            try:
                marketplace = Marketplace.objects.get(code=marketplace_code)
            except Marketplace.DoesNotExist:
                logger.error(f"Marketplace {marketplace_code} not found")
                return
            
            # Create or update combo product
            combo_product, created = ComboProduct.objects.update_or_create(
                combo_sku=combo_sku,
                defaults={
                    'combo_name': fields.get('combo_name', ''),
                    'marketplace': marketplace,
                    'combo_price': fields.get('combo_price', 0),
                    'is_active': fields.get('status') == 'ACTIVE',
                    'is_auto_split': fields.get('is_auto_split', True),
                    'description': fields.get('description', ''),
                    'combo_image_url': fields.get('combo_image_url', '')
                }
            )
            
            action = "Created" if created else "Updated"
            logger.info(f"✅ {action} combo product {combo_sku} from Airtable")
            
        except Exception as e:
            logger.error(f"❌ Failed to sync combo product from Airtable: {e}")

# Create global instance
airtable_sync = AirtableSync()

# =============================================================================
# DJANGO SIGNALS (core/signals.py)
# =============================================================================

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import SKUMapping, Product, ComboProduct, Inventory, InventoryMovement
from .airtable_sync import airtable_sync
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=SKUMapping)
def sync_sku_mapping_on_save(sender, instance, created, **kwargs):
    """Auto-sync SKU mapping to Airtable when saved"""
    try:
        airtable_sync.sync_sku_mapping_to_airtable(instance)
        action = "Created" if created else "Updated"
        logger.info(f"✅ {action} SKU mapping {instance.sku} synced to Airtable")
    except Exception as e:
        logger.error(f"❌ Failed to sync SKU mapping {instance.sku}: {e}")

@receiver(post_save, sender=Product)
def sync_product_on_save(sender, instance, created, **kwargs):
    """Auto-sync product inventory to Airtable when saved"""
    try:
        airtable_sync.sync_product_to_airtable(instance)
        action = "Created" if created else "Updated"
        logger.info(f"✅ {action} product {instance.msku} synced to Airtable")
    except Exception as e:
        logger.error(f"❌ Failed to sync product {instance.msku}: {e}")

@receiver(post_save, sender=ComboProduct)
def sync_combo_product_on_save(sender, instance, created, **kwargs):
    """Auto-sync combo product to Airtable when saved"""
    try:
        airtable_sync.sync_combo_product_to_airtable(instance)
        action = "Created" if created else "Updated"
        logger.info(f"✅ {action} combo product {instance.combo_sku} synced to Airtable")
    except Exception as e:
        logger.error(f"❌ Failed to sync combo product {instance.combo_sku}: {e}")

@receiver(post_save, sender=Inventory)
def sync_inventory_on_save(sender, instance, created, **kwargs):
    """Auto-sync inventory changes to Airtable"""
    try:
        airtable_sync.sync_product_to_airtable(instance.product)
        logger.info(f"✅ Inventory change for {instance.product.msku} synced to Airtable")
    except Exception as e:
        logger.error(f"❌ Failed to sync inventory for {instance.product.msku}: {e}")

@receiver(post_save, sender=InventoryMovement)
def sync_inventory_movement_on_save(sender, instance, created, **kwargs):
    """Auto-sync when inventory movements occur"""
    try:
        airtable_sync.sync_product_to_airtable(instance.product)
        logger.info(f"✅ Inventory movement for {instance.product.msku} synced to Airtable")
    except Exception as e:
        logger.error(f"❌ Failed to sync inventory movement for {instance.product.msku}: {e}")

# =============================================================================
# WEBHOOK HANDLER (core/views.py)
# =============================================================================

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from .airtable_sync import airtable_sync
import json
import hmac
import hashlib
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def airtable_webhook(request):
    """Handle webhooks from Airtable"""
    try:
        body = request.body
        data = json.loads(body.decode('utf-8'))
        
        # Optional signature verification
        if settings.AIRTABLE_WEBHOOK_SECRET:
            signature = request.headers.get('X-Airtable-Content-MAC')
            if signature:
                expected_signature = hmac.new(
                    settings.AIRTABLE_WEBHOOK_SECRET.encode(),
                    body,
                    hashlib.sha256
                ).hexdigest()
                
                if not hmac.compare_digest(f"hmac-sha256={expected_signature}", signature):
                    logger.warning("Invalid webhook signature")
                    return HttpResponse('Invalid signature', status=401)
        
        # Process webhook changes
        for change in data.get('changes', []):
            process_airtable_change(change)
        
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return HttpResponse('Error processing webhook', status=500)

def process_airtable_change(change):
    """Process individual Airtable change"""
    table_id = change.get('tableId')
    record_id = change.get('recordId')
    action = change.get('action')  # 'created', 'updated', 'deleted'
    
    # Map table IDs to handlers
    table_handlers = {
        'tbl0c8O7MWVIRrm96': handle_sku_mapping_change,    # SKU_Mappings
        'tblu0dzhsY7CgW3Qn': handle_combo_product_change,  # Combo_Products
        'tbl2LVelu8mpV6Vkr': handle_inventory_change       # Inventory
    }
    
    handler = table_handlers.get(table_id)
    if handler:
        try:
            # Get full record data for processing
            if action != 'deleted':
                record_data = get_airtable_record(table_id, record_id)
                if record_data:
                    handler(record_data)
            
            logger.info(f"✅ Processed {action} on table {table_id}")
            
        except Exception as e:
            logger.error(f"❌ Error processing change: {e}")
    else:
        logger.warning(f"Unknown table ID in webhook: {table_id}")

def get_airtable_record(table_id: str, record_id: str) -> Optional[Dict]:
    """Get full record data from Airtable"""
    try:
        # Map table IDs to names
        table_names = {
            'tbl0c8O7MWVIRrm96': 'SKU_Mappings',
            'tblu0dzhsY7CgW3Qn': 'Combo_Products', 
            'tbl2LVelu8mpV6Vkr': 'Inventory'
        }
        
        table_name = table_names.get(table_id)
        if not table_name:
            return None
        
        result = airtable_sync._make_request('GET', f"{table_name}/{record_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting record {record_id}: {e}")
        return None

def handle_sku_mapping_change(record_data: Dict):
    """Handle SKU mapping changes from Airtable"""
    airtable_sync.sync_sku_mapping_from_airtable(record_data)

def handle_combo_product_change(record_data: Dict):
    """Handle combo product changes from Airtable"""
    airtable_sync.sync_combo_product_from_airtable(record_data)

def handle_inventory_change(record_data: Dict):
    """Handle inventory changes from Airtable"""
    airtable_sync.sync_inventory_from_airtable(record_data)

# =============================================================================
# MANAGEMENT COMMANDS
# =============================================================================

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

# core/management/commands/test_airtable_connection.py
from django.core.management.base import BaseCommand
from core.airtable_sync import airtable_sync

class Command(BaseCommand):
    help = 'Test Airtable connection and permissions'
    
    def handle(self, *args, **options):
        self.stdout.write("🔍 Testing Airtable connection...")
        
        if airtable_sync._validate_connection():
            self.stdout.write("✅ Connection successful!")
        else:
            self.stdout.write("❌ Connection failed!")

# =============================================================================
# URLS CONFIGURATION
# =============================================================================

# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('webhook/airtable/', views.airtable_webhook, name='airtable_webhook'),
]

# =============================================================================
# APP CONFIGURATION
# =============================================================================

# core/apps.py
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        import core.signals  # Register signals when app starts