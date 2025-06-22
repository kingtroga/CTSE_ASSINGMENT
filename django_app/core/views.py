
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
import pandas as pd
import json

def upload_daily_report(request):
    """Handle daily report uploads and process with Django SKU_Mapper"""
    if request.method == 'POST':
        try:
            # Get uploaded file
            uploaded_file = request.FILES.get('report_file')
            marketplace = request.POST.get('marketplace', 'MISC')
            
            if not uploaded_file:
                return JsonResponse({'error': 'No file uploaded'}, status=400)
            
            # Save file temporarily
            file_path = default_storage.save(f'temp/{uploaded_file.name}', uploaded_file)
            
            # Read uploaded data
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(default_storage.path(file_path))
            elif uploaded_file.name.endswith('.xlsx'):
                df = pd.read_excel(default_storage.path(file_path))
            else:
                return JsonResponse({'error': 'Unsupported file format'}, status=400)
            
            # Process with Django SKU_Mapper
            mapper = DjangoSKUMapper(df)
            mapper.process_sku_mappings()
            mapper.update_inventory()
            
            # Get results
            outbound_data = mapper.get_outbound_data()
            unmapped_skus = mapper.unmapped_skus
            
            # Convert to JSON-serializable format
            if outbound_data is not None:
                outbound_json = outbound_data.to_dict('records')
            else:
                outbound_json = []
            
            # Clean up temp file
            default_storage.delete(file_path)
            
            return JsonResponse({
                'success': True,
                'outbound_data': outbound_json,
                'unmapped_skus': unmapped_skus,
                'total_processed': len(outbound_json),
                'total_unmapped': len(unmapped_skus)
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return render(request, 'core/upload_report.html')

def sync_baserow(request):
    """Trigger Baserow sync via web interface"""
    try:
        from .services.baserow_memory_manager import BaserowMemoryManager
        
        manager = BaserowMemoryManager()
        
        # Get sync type from request
        sync_type = request.GET.get('type', 'full')
        
        if sync_type == 'push':
            # Push Django → Baserow
            sku_results = manager.push_sku_mappings_to_baserow()
            inv_results = manager.push_inventory_to_baserow()
            
            return JsonResponse({
                'success': True,
                'type': 'push',
                'sku_mappings': sku_results,
                'inventory': inv_results
            })
            
        elif sync_type == 'pull':
            # Pull Baserow → Django
            results = manager.pull_sku_mappings_from_baserow()
            
            return JsonResponse({
                'success': True,
                'type': 'pull',
                'results': results
            })
            
        else:
            # Full sync
            results = manager.full_sync_process()
            
            return JsonResponse({
                'success': results['success'],
                'type': 'full',
                'results': results
            })
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
