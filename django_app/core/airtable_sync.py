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
                logger.info("[SUCCESS]  Airtable connection validated successfully")
                return True
            else:
                logger.error(f"[ERROR] Airtable connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"[ERROR] Airtable connection error: {e}")
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
    
    def _get_all_records(self, table_name: str) -> List[Dict]:
        """Get all records from an Airtable table"""
        all_records = []
        offset = None
        
        while True:
            endpoint = table_name
            if offset:
                endpoint += f"?offset={offset}"
            
            result = self._make_request('GET', endpoint)
            records = result.get('records', [])
            all_records.extend(records)
            
            offset = result.get('offset')
            if not offset:
                break
        
        return all_records
    
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
            
            logger.info(f"[SUCCESS] Synced SKU mapping {sku_mapping.sku} to Airtable")
            return record_id
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to sync SKU mapping {sku_mapping.sku}: {e}")
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
            
            logger.info(f"[SUCCESS] Synced inventory for {product.msku} to Airtable")
            return record_id
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to sync inventory for {product.msku}: {e}")
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
            
            logger.info(f"[SUCCESS] Synced combo product {combo_product.combo_sku} to Airtable")
            return record_id
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to sync combo product {combo_product.combo_sku}: {e}")
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
            logger.info(f"[SUCCESS] {action} SKU mapping {sku} from Airtable")
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to sync SKU mapping from Airtable: {e}")
    
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
                            
                            logger.info(f"[SUCCESS] Updated {msku} stock at {warehouse_code}: {old_stock} → {new_stock}")
                    
                    except Exception as e:
                        logger.error(f"Error updating {warehouse_code} stock: {e}")
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to sync inventory from Airtable: {e}")
    
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
            logger.info(f"[SUCCESS] {action} combo product {combo_sku} from Airtable")
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to sync combo product from Airtable: {e}")
    
    # =============================================================================
    # AIRTABLE → DJANGO BULK SYNC (for cron jobs)
    # =============================================================================
    
    def sync_from_airtable(self, model_type: str = 'all', limit: Optional[int] = None) -> Dict[str, int]:
        """Sync data FROM Airtable TO Django (for cron jobs)"""
        results = {'created': 0, 'updated': 0, 'errors': 0}
        
        try:
            if model_type in ['all', 'inventory']:
                logger.info("🔄 Syncing inventory FROM Airtable TO Django...")
                airtable_records = self._get_all_records('Inventory')
                
                for record in airtable_records[:limit] if limit else airtable_records:
                    try:
                        self.sync_inventory_from_airtable(record)
                        results['updated'] += 1
                    except Exception as e:
                        logger.error(f"Error syncing inventory record: {e}")
                        results['errors'] += 1
            
            if model_type in ['all', 'sku_mappings']:
                logger.info("[OPERATION] Syncing SKU mappings FROM Airtable TO Django...")
                airtable_records = self._get_all_records('SKU_Mappings')
                
                for record in airtable_records[:limit] if limit else airtable_records:
                    try:
                        self.sync_sku_mapping_from_airtable(record)
                        results['updated'] += 1
                    except Exception as e:
                        logger.error(f"Error syncing SKU mapping record: {e}")
                        results['errors'] += 1
            
            if model_type in ['all', 'combo_products']:
                logger.info("[OPERATION] Syncing combo products FROM Airtable TO Django...")
                airtable_records = self._get_all_records('Combo_Products')
                
                for record in airtable_records[:limit] if limit else airtable_records:
                    try:
                        self.sync_combo_product_from_airtable(record)
                        results['updated'] += 1
                    except Exception as e:
                        logger.error(f"Error syncing combo product record: {e}")
                        results['errors'] += 1
            
            logger.info(f"[SUCCESS] Sync from Airtable complete: {results}")
            return results
            
        except Exception as e:
            logger.error(f"[ERROR] Error in sync_from_airtable: {e}")
            results['errors'] += 1
            return results

# Create global instance
airtable_sync = AirtableSync()