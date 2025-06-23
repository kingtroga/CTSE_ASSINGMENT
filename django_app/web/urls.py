# django_app/web/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.process_sales_data, name='process_sales_data'),
    path('download/', views.download_outbound_csv, name='download_outbound_csv'),
    path('status/', views.get_system_status, name='get_system_status'),
    path('unmapped/', views.get_unmapped_skus, name='get_unmapped_skus'),
]

