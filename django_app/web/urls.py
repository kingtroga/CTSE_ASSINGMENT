# django_app/web/urls.py
from django.urls import path
from . import views

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
]