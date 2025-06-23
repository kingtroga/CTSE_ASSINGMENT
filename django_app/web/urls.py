# django_app/web/urls.py - ADD these new URL patterns
from django.urls import path
from . import views
from . import smart_assistant  # Import the new smart_assistant module

app_name = 'web'

urlpatterns = [
    # Main processing view
    path('', views.process_sales_data, name='process_sales_data'),
    
    # Real-time log streaming
    path('stream-logs/<str:session_id>/', views.stream_logs, name='stream_logs'),
    
    # Download processed CSV
    path('download/', views.download_outbound_csv, name='download_outbound_csv'),
    
    # System status
    path('status/', views.get_system_status, name='get_system_status'),
    
    # Get unmapped SKUs
    path('unmapped/', views.get_unmapped_skus, name='get_unmapped_skus'),
    
    # NEW: Smart Assistant URLs
    path('assistant/', smart_assistant.smart_assistant, name='smart_assistant'),
    path('assistant/suggestions/', smart_assistant.get_query_suggestions, name='query_suggestions'),
]