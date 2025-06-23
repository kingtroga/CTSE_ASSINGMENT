
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from .airtable_sync import airtable_sync
from typing import Dict, Optional
import json
import hmac
import hashlib
import logging
from django.shortcuts import render

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
            
            logger.info(f"[SUCCESS] Processed {action} on table {table_id}")
            
        except Exception as e:
            logger.error(f"[ERROR] Error processing change: {e}")
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

def custom_404_view(request, exception):
    return render(request, 'core/404.html', status=404)

def custom_500_view(request):
    return render(request, 'core/500.html', status=500)