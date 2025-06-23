# django_app/web/views.py (or wherever your views are)
# =============================================================================
# Django Views for SKU Mapper Integration
# =============================================================================

import os
import json
import pandas as pd
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import tempfile
import sys
from pathlib import Path

def _import_processors(): 
    # Import here, after paths are set
    from flexible_input_processor import FlexibleInputProcessor
    from sku_mapper.core_code.mapper import SKUMapper
    
    return FlexibleInputProcessor, SKUMapper


@csrf_exempt
@require_http_methods(["GET", "POST"])
def process_sales_data(request):
    """Main view for processing sales data files"""
    
    if request.method == 'GET':
        # Return the upload form
        return render(request, 'web/upload_form.html', {
            'marketplaces': [
                'CSTE_AMAZON',
                'CSTE_FK', 
                'CSTE_MEESHO',
                'GL_FK',
                'RUDRAV_MEESHO'
            ]
        })
    
    elif request.method == 'POST':
        try:

            # Get uploaded file
            uploaded_file = request.FILES.get('sales_file')
            marketplace = request.POST.get('marketplace', '')
            
            if not uploaded_file:
                return JsonResponse({
                    'success': False,
                    'error': 'No file uploaded'
                }, status=400)
            
            if not marketplace:
                return JsonResponse({
                    'success': False,
                    'error': 'No marketplace selected'
                }, status=400)
            
            # Process the file
            result = process_uploaded_file(uploaded_file, marketplace)
            
            if result['success']:
                return JsonResponse(result)
            else:
                return JsonResponse(result, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Server error: {str(e)}'
            }, status=500)


def process_uploaded_file(uploaded_file, marketplace):
    """Process uploaded file and return results"""
    
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'_{uploaded_file.name}') as temp_file:
            # Write uploaded content to temporary file
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        
        try:
            # Import processors
            FlexibleInputProcessor, SKUMapper = _import_processors()

            # Step 1: Process file using FlexibleInputProcessor
            processor = FlexibleInputProcessor(verbose=True, auto_install=False)
            report_data = processor.process_file(temp_file_path)
            
            if report_data is None or report_data.empty:
                return {
                    'success': False,
                    'error': 'Failed to process file. Please check file format.'
                }
            
            # Step 2: Initialize SKU Mapper with Django integration
            mapper = SKUMapper(report_data, use_django=True)  # Enable Django mode
            
            # Step 3: Process SKU mappings with marketplace filter
            mapper.process_sku_mappings(marketplace_filter=marketplace)
            
            # Step 4: Update inventory
            mapper.update_inventory()
            
            # Step 5: Get outbound data
            outbound_data = mapper.get_outbound_data()
            
            if outbound_data is None or outbound_data.empty:
                return {
                    'success': False,
                    'error': 'No valid data found after processing'
                }
            
            # Step 6: Get processing summary
            summary = mapper.get_processing_summary()
            
            # Step 7: Convert outbound data to JSON for response
            outbound_json = outbound_data.to_dict('records')
            
            # Step 8: Create downloadable CSV
            csv_content = outbound_data.to_csv(index=False)
            
            return {
                'success': True,
                'data': {
                    'outbound_data': outbound_json,
                    'summary': summary,
                    'csv_content': csv_content,
                    'filename': f"{marketplace.lower()}_outbound_{uploaded_file.name.split('.')[0]}.csv"
                },
                'message': f'Successfully processed {len(outbound_data)} records'
            }
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass
    
    except Exception as e:
        return {
            'success': False,
            'error': f'Processing error: {str(e)}'
        }


@csrf_exempt
@require_http_methods(["POST"])
def download_outbound_csv(request):
    """Download processed outbound data as CSV"""
    
    try:
        data = json.loads(request.body)
        csv_content = data.get('csv_content', '')
        filename = data.get('filename', 'outbound_data.csv')
        
        if not csv_content:
            return JsonResponse({
                'success': False,
                'error': 'No CSV content provided'
            }, status=400)
        
        # Create HTTP response with CSV content
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Download error: {str(e)}'
        }, status=500)


def get_system_status(request):
    """Get system status and statistics"""
    
    try:
        # Import Django models to get current stats
        from core.models import Product, SKUMapping, Warehouse, Inventory
        
        stats = {
            'total_products': Product.objects.count(),
            'active_products': Product.objects.filter(is_active=True).count(),
            'total_sku_mappings': SKUMapping.objects.count(),
            'active_sku_mappings': SKUMapping.objects.filter(status='ACTIVE').count(),
            'total_warehouses': Warehouse.objects.count(),
            'low_stock_items': Inventory.objects.filter(current_stock__lte=10).count(),
            'marketplaces': [
                'CSTE_AMAZON',
                'CSTE_FK', 
                'CSTE_MEESHO',
                'GL_FK',
                'RUDRAV_MEESHO'
            ]
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Status error: {str(e)}'
        }, status=500)


# =============================================================================
# Additional utility views
# =============================================================================

def get_unmapped_skus(request):
    """Get list of unmapped SKUs for review"""
    
    try:
        # This would be called after processing to show unmapped SKUs
        marketplace = request.GET.get('marketplace', '')
        
        # For now, return empty list - in production you'd store unmapped SKUs
        # in session or database for retrieval
        
        return JsonResponse({
            'success': True,
            'unmapped_skus': [],
            'marketplace': marketplace
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error getting unmapped SKUs: {str(e)}'
        }, status=500)