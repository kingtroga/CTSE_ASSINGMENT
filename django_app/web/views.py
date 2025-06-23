# django_app/web/views.py
# =============================================================================
# Django Views with Real-Time Log Streaming from Actual Log Files
# =============================================================================

import os
import json
import pandas as pd
import threading
import time
import logging
from pathlib import Path
from queue import Queue
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import tempfile
import sys

# Global queue for log streaming
log_queue = Queue()

class LogFileWatcher:
    """Watch multiple log files and stream new lines to queue"""
    
    def __init__(self, session_id):
        self.session_id = session_id
        self.log_files = {
            'sku_mapping': Path(settings.BASE_DIR) / 'logs' / 'sku_mapping.log',
            'airtable_sync': Path(settings.BASE_DIR) / 'logs' / 'airtable_sync.log', 
            'flexible_processor': Path(settings.BASE_DIR) / 'logs' / 'flexible_input_processor.log',
        }
        self.file_positions = {}
        self.watching = False
        self.watch_thread = None
        
    def start_watching(self):
        """Start watching log files"""
        self.watching = True
        
        # Initialize file positions to end of files
        for name, path in self.log_files.items():
            if path.exists():
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(0, 2)  # Seek to end
                    self.file_positions[name] = f.tell()
            else:
                self.file_positions[name] = 0
        
        # Start watching thread
        self.watch_thread = threading.Thread(target=self._watch_files)
        self.watch_thread.daemon = True
        self.watch_thread.start()
    
    def stop_watching(self):
        """Stop watching log files"""
        self.watching = False
        if self.watch_thread:
            self.watch_thread.join(timeout=1)
    
    def _watch_files(self):
        """Watch files for new content"""
        while self.watching:
            try:
                for name, path in self.log_files.items():
                    if path.exists():
                        self._check_file_for_new_lines(name, path)
                
                time.sleep(0.5)  # Check every 500ms
                
            except Exception as e:
                print(f"Error watching log files: {e}")
                time.sleep(1)
    
    def _check_file_for_new_lines(self, name, path):
        """Check a single file for new lines"""
        try:
            current_size = path.stat().st_size
            last_position = self.file_positions.get(name, 0)
            
            if current_size > last_position:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(last_position)
                    new_lines = f.readlines()
                    self.file_positions[name] = f.tell()
                    
                    # Process new lines
                    for line in new_lines:
                        line = line.strip()
                        if line:
                            self._process_log_line(name, line)
            
        except Exception as e:
            print(f"Error checking {name}: {e}")
    
    def _process_log_line(self, source, line):
        """Process a log line and add to queue"""
        try:
            # Parse different log formats
            log_entry = self._parse_log_line(source, line)
            
            if log_entry:
                log_queue.put({
                    'session_id': self.session_id,
                    'source': source,
                    'timestamp': time.strftime('%H:%M:%S'),
                    'message': log_entry['message'],
                    'level': log_entry.get('level', 'INFO'),
                    'component': log_entry.get('component', source.upper())
                })
                
        except Exception as e:
            print(f"Error processing log line from {source}: {e}")
    
    def _parse_log_line(self, source, line):
        """Parse different log line formats"""
        try:
            if source == 'sku_mapping':
                # Format: "2025-06-23 08:38:25,078 - INFO - MAPPER | STARTED | Processing SKU mappings"
                if ' - INFO - ' in line:
                    parts = line.split(' - INFO - ', 1)
                    if len(parts) == 2:
                        message = parts[1]
                        # Extract component if present
                        if ' | ' in message:
                            comp_parts = message.split(' | ', 2)
                            if len(comp_parts) >= 3:
                                return {
                                    'component': comp_parts[0],
                                    'action': comp_parts[1], 
                                    'message': comp_parts[2],
                                    'level': 'INFO'
                                }
                        return {'message': message, 'level': 'INFO'}
            
            elif source == 'airtable_sync':
                # Format: "2025-06-23 08:38:28,245 - INFO - [SUCCESS] Synced inventory for..."
                if ' - INFO - ' in line:
                    parts = line.split(' - INFO - ', 1)
                    if len(parts) == 2:
                        message = parts[1]
                        level = 'SUCCESS' if '[SUCCESS]' in message else 'INFO'
                        return {'message': message, 'level': level}
            
            elif source == 'flexible_processor':
                # Format: "2025-06-23 08:37:45,877 - FlexibleInputProcessor - INFO - Processing file:"
                if ' - FlexibleInputProcessor - INFO - ' in line:
                    parts = line.split(' - FlexibleInputProcessor - INFO - ', 1)
                    if len(parts) == 2:
                        return {'message': parts[1], 'level': 'INFO', 'component': 'FILE_PROCESSOR'}
            
            # Fallback - return as-is
            return {'message': line, 'level': 'INFO'}
            
        except Exception as e:
            return {'message': line, 'level': 'INFO'}

# Global watchers dict
active_watchers = {}

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
            
            # Generate session ID
            session_id = str(int(time.time() * 1000000))
            
            # Start log watcher for this session
            watcher = LogFileWatcher(session_id)
            active_watchers[session_id] = watcher
            watcher.start_watching()
            
            # Process the file with immediate data return
            result = process_uploaded_file_immediate(uploaded_file, marketplace, session_id)
            
            if result['success']:
                result['session_id'] = session_id
                return JsonResponse(result)
            else:
                # Clean up watcher on error
                watcher.stop_watching()
                del active_watchers[session_id]
                return JsonResponse(result, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Server error: {str(e)}'
            }, status=500)


def process_uploaded_file_immediate(uploaded_file, marketplace, session_id):
    """Process uploaded file and return data immediately, sync inventory in background"""
    
    try:
        # Add initial log entry
        log_queue.put({
            'session_id': session_id,
            'source': 'system',
            'timestamp': time.strftime('%H:%M:%S'),
            'message': f'Starting processing for {marketplace}...',
            'level': 'INFO',
            'component': 'SYSTEM'
        })
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'_{uploaded_file.name}') as temp_file:
            # Write uploaded content to temporary file
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        
        try:
            # Import processors
            FlexibleInputProcessor, SKUMapper = _import_processors()

            log_queue.put({
                'session_id': session_id,
                'source': 'system',
                'timestamp': time.strftime('%H:%M:%S'),
                'message': 'Processing file with FlexibleInputProcessor...',
                'level': 'INFO',
                'component': 'FILE_PROCESSOR'
            })

            # Step 1: Process file using FlexibleInputProcessor
            processor = FlexibleInputProcessor(verbose=True, auto_install=False)
            report_data = processor.process_file(temp_file_path)
            
            if report_data is None or report_data.empty:
                return {
                    'success': False,
                    'error': 'Failed to process file. Please check file format.'
                }
            
            log_queue.put({
                'session_id': session_id,
                'source': 'system',
                'timestamp': time.strftime('%H:%M:%S'),
                'message': f'File processed: {len(report_data)} rows loaded',
                'level': 'SUCCESS',
                'component': 'FILE_PROCESSOR'
            })

            # Step 2: Initialize SKU Mapper with Django integration
            log_queue.put({
                'session_id': session_id,
                'source': 'system',
                'timestamp': time.strftime('%H:%M:%S'),
                'message': 'Initializing SKU Mapper with Django integration...',
                'level': 'INFO',
                'component': 'SKU_MAPPER'
            })
            
            mapper = SKUMapper(report_data, use_django=True)  # Enable Django mode
            
            # Step 3: Process SKU mappings with marketplace filter
            log_queue.put({
                'session_id': session_id,
                'source': 'system',
                'timestamp': time.strftime('%H:%M:%S'),
                'message': f'Processing SKU mappings for {marketplace}...',
                'level': 'INFO',
                'component': 'SKU_MAPPER'
            })
            
            mapper.process_sku_mappings(marketplace_filter=marketplace)
            
            # Step 4: Get outbound data IMMEDIATELY (before inventory update)
            outbound_data = mapper.get_outbound_data()
            
            if outbound_data is None or outbound_data.empty:
                return {
                    'success': False,
                    'error': 'No valid data found after processing'
                }
            
            # Step 5: Get processing summary
            summary = mapper.get_processing_summary()
            
            # Step 6: Convert outbound data to JSON for response
            outbound_json = outbound_data.to_dict('records')
            
            # Step 7: Create downloadable CSV
            csv_content = outbound_data.to_csv(index=False)
            
            log_queue.put({
                'session_id': session_id,
                'source': 'system',
                'timestamp': time.strftime('%H:%M:%S'),
                'message': f'Your data is ready! {len(outbound_data)} records processed',
                'level': 'SUCCESS',
                'component': 'SYSTEM'
            })
            
            # Step 8: Start background inventory update in separate thread
            def background_inventory_sync():
                """Run inventory update in background"""
                try:
                    log_queue.put({
                        'session_id': session_id,
                        'source': 'system',
                        'timestamp': time.strftime('%H:%M:%S'),
                        'message': 'Starting background inventory sync...',
                        'level': 'INFO',
                        'component': 'INVENTORY'
                    })
                    
                    mapper.update_inventory()
                    
                    log_queue.put({
                        'session_id': session_id,
                        'source': 'system',
                        'timestamp': time.strftime('%H:%M:%S'),
                        'message': 'Background inventory sync completed!',
                        'level': 'SUCCESS',
                        'component': 'INVENTORY'
                    })
                    
                    # Stop log watcher after completion
                    time.sleep(2)  # Give logs time to be read
                    if session_id in active_watchers:
                        active_watchers[session_id].stop_watching()
                        del active_watchers[session_id]
                        
                except Exception as e:
                    log_queue.put({
                        'session_id': session_id,
                        'source': 'system',
                        'timestamp': time.strftime('%H:%M:%S'),
                        'message': f'Background sync failed: {str(e)}',
                        'level': 'ERROR',
                        'component': 'INVENTORY'
                    })
            
            # Start background thread
            sync_thread = threading.Thread(target=background_inventory_sync)
            sync_thread.daemon = True
            sync_thread.start()
            
            return {
                'success': True,
                'data': {
                    'outbound_data': outbound_json,
                    'summary': summary,
                    'csv_content': csv_content,
                    'filename': f"{marketplace.lower()}_outbound_{uploaded_file.name.split('.')[0]}.csv"
                },
                'message': f'Successfully processed {len(outbound_data)} records',
                'warning': 'Your data is ready for download! Please keep this page open while we update inventory in the background.',
                'background_sync': True
            }
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass
    
    except Exception as e:
        log_queue.put({
            'session_id': session_id,
            'source': 'system',
            'timestamp': time.strftime('%H:%M:%S'),
            'message': f'Error: {str(e)}',
            'level': 'ERROR',
            'component': 'SYSTEM'
        })
        
        return {
            'success': False,
            'error': f'Processing error: {str(e)}'
        }


def stream_logs(request, session_id):
    """Stream real-time logs from actual log files"""
    
    def event_stream():
        """Generator function for Server-Sent Events"""
        last_heartbeat = time.time()
        
        while True:
            try:
                # Get log entry from queue (timeout after 1 second)
                log_entry = log_queue.get(timeout=1.0)
                
                # Only send logs for this session
                if log_entry['session_id'] == session_id:
                    # Format as Server-Sent Event
                    yield f"data: {json.dumps(log_entry)}\n\n"
                    last_heartbeat = time.time()
                    
            except:
                # Send heartbeat every 30 seconds to keep connection alive
                if time.time() - last_heartbeat > 30:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                    last_heartbeat = time.time()
                    
                # Stop streaming after 10 minutes if no activity
                if session_id not in active_watchers and time.time() - last_heartbeat > 600:
                    break
    
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
    
    return response


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